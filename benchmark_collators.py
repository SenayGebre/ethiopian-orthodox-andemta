import asyncio
import json
import os
import time
import cv2
import numpy as np
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional

load_dotenv()

class UncertainSpan(BaseModel):
    printed_text: str = Field(description="Exact characters as transcribed in text")
    alternative: str = Field(description="Alternative reading or editorial correction if printed_text is a print typo or faded")
    note: str = Field(description="Brief reason: faded ink, print typo, or ambiguous Fidel order")

class DiplomaticLine(BaseModel):
    line_num: int
    margin_tag: Optional[str] = Field(default=None, description="Ethiopic verse number in left margin if present (e.g. ፩, ፪, ፳፭)")
    line_type: str = Field(default="body", description="chapter_title | section_title | body")
    text: str = Field(description="Exact line text. Wrap root Gospel of Matthew Ge'ez verse words in ⟪...⟫ so root scripture is distinguished from commentary.")
    word_wraps_to_next_line: bool = Field(default=False, description="True if the last word on this line is split mid-word and continues on the next line")
    uncertain: List[UncertainSpan] = Field(default_factory=list)

class ColumnTranscription(BaseModel):
    column_index: int
    lines: List[DiplomaticLine]

class PageTranscription(BaseModel):
    running_header: str
    columns: List[ColumnTranscription]

def prepare_page_crops(pdf_page: int):
    img_bgr = cv2.imread(f"data/raw_images/page_{pdf_page:03d}.jpg")
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    roi = gray[int(h*0.28):int(h*0.85), :]
    _, bw = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    col_proj = np.sum(bw, axis=0) / 255.0
    smooth = np.convolve(col_proj, np.ones(15)/15.0, mode="same")
    g1 = int(w*0.28) + int(np.argmin(smooth[int(w*0.28):int(w*0.44)]))
    g2 = int(w*0.56) + int(np.argmin(smooth[int(w*0.56):int(w*0.72)]))

    y0 = int(h * 0.26) if pdf_page == 1 else int(h * 0.06)
    c1 = img_bgr[y0:, 0:min(w, g1+18)]
    c2 = img_bgr[y0:, max(0, g1-24):min(w, g2+18)]
    c3 = img_bgr[y0:, max(0, g2-24):w]

    def to_pil_2x(arr):
        up = cv2.resize(arr, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_LANCZOS4)
        return Image.fromarray(cv2.cvtColor(up, cv2.COLOR_BGR2RGB))

    full_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    return full_pil, to_pil_2x(c1), to_pil_2x(c2), to_pil_2x(c3)

PROMPT_TEMPLATE = """You are the world's foremost philologist in Classical Ethiopic (Ge'ez / ግዕዝ) and Ethiopian Orthodox Andemta Commentary (ወንጌለ ማቴዎስ አንድምታ ትርጓሜ).
Transcribe PDF Page {pdf_page} (Book Page {book_page}) with 100% character-level fidelity.

Images provided:
1. Full page image
2. Column 1 (left) 2x zoom including left margin
3. Column 2 (middle) 2x zoom including left margin
4. Column 3 (right) 2x zoom including left margin

STRICT PHILOLOGICAL & OCR RULES:
1. Transcribe EVERY physical line of Column 1, Column 2, and Column 3 in exact top-to-bottom order. Never skip or merge lines.
2. Preserve exact Ethiopic Fidels (ሀ/ሐ/ኀ, ሰ/ሠ, አ/ዐ, ጸ/ፀ, ቍ/ቁ, ኵ/ኩ) and exact punctuation (፡, ።, ፤, ፥).
3. Wrap the root Gospel of Matthew Ge'ez verse words/phrases in ⟪...⟫ (e.g. ⟪መጽሐፈ ልደቱ ለእግ⟫ / ⟪ዚእነ ኢየሱስ ክርስቶስ ።⟫ or ⟪አብርሃም ወለደ ለይስሐቅ ።⟫). Do NOT wrap patristic/other biblical citations or Amharic commentary in ⟪...⟫ unless it is the Matthew verse lemma being commented on.
4. Set `word_wraps_to_next_line = true` whenever the last word of a line splits mid-word onto the next line (e.g., `ለእግ` -> `ዚእነ`, `ራሳቸው` -> `ን`, `በጥቁ` -> `ር`).
5. Watch carefully for technical Andemta terms (`ንዑስ ምዕራፍ አኀዝ ነው`, `በጥቁር`, `ሰንጠረጅ`, `አንድም`, `ሐተታ`, `ታሪክ`, `ምሳሌ`, `ወንጌላوي`) and biblical names (`ትእማር`, `ራኬብ`, `ሩት`, `ይስሐቅ`, `ያዕቆብ`, `ይሁዳ`, `ፋሬስ`, `ዛራ`, `ኤስሮም`, `አራም`, `አሚናዳብ`, `ነአሶን`, `ሰልሞን`, `ቦኤዝ`, `ኢዮቤድ`, `እሴይ`, `ዳዊት`, `ሰሎሞን`, `ሮብዓም`, `አብያ`, `አሳፍ`, `ኢዮสาፍጥ`, `ኢዮራም`, `ዖዝያን`, `ኢዮአታም`, `አካዝ`, `ሕዝቅያስ`, `ምናሴ`, `አሞፅ`, `ኢዮስያስ`, `ኢኮንያን`, `ሰላትያል`, `ዘሩባቤል`).
6. Whenever a character has faded ink, broken strokes, or a print typo (like `ከራቸሳው` or missing `ኒ` in `የለ ህ`), record the exact printed letters in `text` and add an entry in `uncertain` with the intended reading in `alternative`.
"""

async def test_single(client, model_name: str, pdf_page: int):
    full_pil, c1, c2, c3 = prepare_page_crops(pdf_page)
    book_page = 119 + pdf_page
    prompt = PROMPT_TEMPLATE.format(pdf_page=pdf_page, book_page=book_page)
    t0 = time.time()
    resp = await client.aio.models.generate_content(
        model=model_name,
        contents=[full_pil, c1, c2, c3, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PageTranscription,
            temperature=0.0,
        ),
    )
    dt = time.time() - t0
    data = json.loads(resp.text)
    lines_cnt = [len(c["lines"]) for c in data["columns"]]
    print(f"[{model_name}] Page {pdf_page}: {dt:.1f}s | lines={lines_cnt}")
    return data

async def main():
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    t0 = time.time()
    res = await asyncio.gather(
        test_single(client, "gemini-4-argon", 1),
        test_single(client, "gemini-4-argon", 2),
        test_single(client, "gemini-3.8-flash", 1),
        test_single(client, "gemini-3.8-flash", 2),
    )
    print(f"Total parallel wall time: {time.time() - t0:.1f}s")
    with open("data/debug_crops/bench_p1_argon.json", "w", encoding="utf-8") as f:
        json.dump(res[0], f, ensure_ascii=False, indent=2)
    with open("data/debug_crops/bench_p2_argon.json", "w", encoding="utf-8") as f:
        json.dump(res[1], f, ensure_ascii=False, indent=2)
    with open("data/debug_crops/bench_p1_flash.json", "w", encoding="utf-8") as f:
        json.dump(res[2], f, ensure_ascii=False, indent=2)
    with open("data/debug_crops/bench_p2_flash.json", "w", encoding="utf-8") as f:
        json.dump(res[3], f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
