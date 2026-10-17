import asyncio
import json
import os
import sys
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

PAGES_DIR = "data/extracted/pages"
CROPS_DIR = "data/extracted/crops"
os.makedirs(PAGES_DIR, exist_ok=True)
os.makedirs(CROPS_DIR, exist_ok=True)

ETHIOPIC_UNITS = ["", "፩", "፪", "፫", "፬", "፭", "፮", "፯", "፰", "፱"]
ETHIOPIC_TENS = ["", "፲", "፳", "፴", "፵", "፶", "፷", "፸", "፹", "፺"]

def int_to_ethiopic(n: int) -> str:
    if n <= 0:
        return ""
    if n >= 100:
        hundreds = n // 100
        rem = n % 100
        h_prefix = "" if hundreds == 1 else ETHIOPIC_UNITS[hundreds]
        return f"{h_prefix}፻{int_to_ethiopic(rem)}"
    tens = n // 10
    units = n % 10
    return f"{ETHIOPIC_TENS[tens]}{ETHIOPIC_UNITS[units]}"

def get_book_page_number(pdf_page: int) -> Optional[int]:
    if pdf_page in (188, 194, 201):
        return None
    if 1 <= pdf_page <= 193:
        return 119 + pdf_page
    if 195 <= pdf_page <= 200:
        return 118 + pdf_page
    return None

# --- Schemas ---

class UncertainSpan(BaseModel):
    printed_text: str = Field(description="Exact characters as transcribed in text")
    alternative: str = Field(description="Alternative reading or editorial correction if printed_text is a print typo or faded")
    note: str = Field(description="Brief reason: faded ink, print typo, or ambiguous Fidel order")

class DiplomaticLine(BaseModel):
    line_num: int
    margin_tag: Optional[str] = Field(default=None, description="Ethiopic verse number in left margin if present (e.g. ፩, ፪, ፳፭)")
    line_type: str = Field(default="body", description="chapter_title | section_title | body | colophon")
    text: str = Field(description="Exact line text. Wrap root Gospel of Matthew Ge'ez verse words in ⟪...⟫ so root scripture is distinguished from commentary.")
    word_wraps_to_next_line: bool = Field(default=False, description="True if the last word on this line is split mid-word and continues on the next line")
    uncertain: List[UncertainSpan] = Field(default_factory=list)

class ColumnTranscription(BaseModel):
    column_index: int
    lines: List[DiplomaticLine]

class PageTranscription(BaseModel):
    running_header: str
    columns: List[ColumnTranscription]

class TocEntry(BaseModel):
    row_num: int
    geez_title: str = Field(description="Left column Ge'ez topic/chapter entry")
    chapter_ethiopic: Optional[str] = Field(default=None, description="Chapter number in Ethiopic numerals (e.g. ፩, ፪) if printed on this row")
    verse_ethiopic: Optional[str] = Field(default=None, description="Verse number in Ethiopic numerals (e.g. ፩, ፲፰) if printed on this row")
    amharic_title: str = Field(description="Right column Amharic topic/chapter entry")
    uncertain: List[UncertainSpan] = Field(default_factory=list)

class TocPageTranscription(BaseModel):
    running_header_geez: str
    running_header_amharic: str
    entries: List[TocEntry]
    columns: List[ColumnTranscription] = Field(description="Line-by-line diplomatic transcription of Left column (column_index=1) and Right column (column_index=2)")

class IllustrationPageTranscription(BaseModel):
    title_inscription: str
    caption_lines: List[DiplomaticLine]
    description: str

# --- Image Preparation ---

def prepare_3col_crops(pdf_page: int):
    img_bgr = cv2.imread(f"data/raw_images/page_{pdf_page:03d}.jpg")
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    roi_y1 = int(h * 0.55) if pdf_page == 192 else int(h * 0.85)
    roi = gray[int(h * 0.20):roi_y1, :]
    _, bw = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    col_proj = np.sum(bw, axis=0) / 255.0
    smooth = np.convolve(col_proj, np.ones(15) / 15.0, mode="same")
    g1 = int(w * 0.28) + int(np.argmin(smooth[int(w * 0.28):int(w * 0.44)]))
    g2 = int(w * 0.56) + int(np.argmin(smooth[int(w * 0.56):int(w * 0.72)]))

    y0 = int(h * 0.26) if pdf_page == 1 else int(h * 0.06)
    y1 = int(h * 0.65) if pdf_page == 192 else h

    boxes = [
        [0, y0, min(w, g1 + 18), y1],
        [max(0, g1 - 24), y0, min(w, g2 + 18), y1],
        [max(0, g2 - 24), y0, w, y1],
    ]
    crops = []
    for bx in boxes:
        sub = img_bgr[bx[1]:bx[3], bx[0]:bx[2]]
        up = cv2.resize(sub, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_LANCZOS4)
        crops.append(Image.fromarray(cv2.cvtColor(up, cv2.COLOR_BGR2RGB)))

    full_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    return full_pil, crops, boxes

def prepare_toc_crops(pdf_page: int):
    img_bgr = cv2.imread(f"data/raw_images/page_{pdf_page:03d}.jpg")
    h, w, _ = img_bgr.shape
    top_band = img_bgr[int(h * 0.05):int(h * 0.55), :]
    bot_band = img_bgr[int(h * 0.48):h, :]
    up_top = cv2.resize(top_band, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_LANCZOS4)
    up_bot = cv2.resize(bot_band, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_LANCZOS4)
    full_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    return full_pil, Image.fromarray(cv2.cvtColor(up_top, cv2.COLOR_BGR2RGB)), Image.fromarray(cv2.cvtColor(up_bot, cv2.COLOR_BGR2RGB))

PROMPT_3COL = """You are the world's foremost philologist in Classical Ethiopic (Ge'ez / ግዕዝ) and Ethiopian Orthodox Andemta Commentary (ወንጌለ ማቴዎስ አንድምታ ትርጓሜ).
Transcribe PDF Page {pdf_page} (Book Page {book_page_eth} / {book_page_num}) with 100% character-level fidelity.

Images provided:
1. Full page image
2. Column 1 (left) 2x zoom including left margin
3. Column 2 (middle) 2x zoom including left margin
4. Column 3 (right) 2x zoom including left margin

STRICT PHILOLOGICAL & OCR RULES:
1. Transcribe EVERY physical line of Column 1, Column 2, and Column 3 in exact top-to-bottom order. Never skip or merge lines.
2. Preserve exact Ethiopic Fidels (ሀ/ሐ/ኀ, ሰ/ሠ, አ/ዐ, ጸ/ፀ, ቍ/ቁ, ኵ/ኩ) and exact punctuation (፡, ።, ፤, ፥). Do NOT modernize archaic forms (keep ሁነው, ለኒህ, ደንጊያ, ፩ዱ, etc. exactly as printed).
3. Wrap the root Gospel of Matthew Ge'ez verse words/phrases in ⟪...⟫ (e.g. ⟪መጽሐፈ ልደቱ ለእግ⟫ / ⟪ዚእነ ኢየሱስ ክርስቶስ ።⟫ or ⟪አብርሃም ወለደ ለይስሐቅ ።⟫). Do NOT wrap patristic/other biblical citations or Amharic commentary in ⟪...⟫ unless it is the Matthew verse lemma being commented on.
4. Set `line_type` to:
   - `"chapter_title"` for major chapter headings like `ምዕራፍ ፩ ።`, `ምዕራፍ ፪ ።`
   - `"section_title"` for pericope subheadings like `በእንተ መናፍስት ርኩሳን ።`, `ዘከመ ተቀብረ ኢየሱስ ።`
   - `"colophon"` for concluding colophon lines at the end of the book
   - `"body"` for all standard verse and commentary lines
5. Record any Ethiopic verse numeral printed in the left margin of a line in `margin_tag` (e.g. `"፩"`, `"፪"`, `"፳፭"`).
6. Set `word_wraps_to_next_line = true` whenever the last word of a line splits mid-word onto the next line (e.g., `ለእግ` -> `ዚእነ`, `ራሳቸው` -> `ን`, `በጥቁ` -> `ር`).
7. Whenever a character has faded ink, broken strokes, or a print typo (like `ከራቸሳው` or missing `ኒ` in `የለ ህ`), record the exact printed letters in `text` and add an entry in `uncertain` with the intended reading in `alternative`.
"""

PROMPT_TOC = """You are the world's foremost philologist in Classical Ethiopic (Ge'ez / ግዕዝ) and Ethiopian Orthodox Andemta Commentary (ወንጌለ ማቴዎስ አንድምታ ትርጓሜ).
Transcribe this Index / Table of Contents page (PDF Page {pdf_page}, Book Page {book_page_eth} / {book_page_num}) with 100% character-level fidelity.

Images provided:
1. Full page image
2. Top half 2x zoom
3. Bottom half 2x zoom

RULES:
1. In `entries`, extract every row of the parallel index table in top-to-bottom order:
   - `geez_title`: the Ge'ez entry on the left (e.g., `ምዕራፍ ፩ መጽሐፈ ልደቱ ።` or `በእንተ መጽሐፈ ትውልድ ዘኢየሱስ ክርስቶስ ።`)
   - `chapter_ethiopic`: the chapter numeral (`ም`) if present on this row (or inherited chapter if blank, or exact printed numeral)
   - `verse_ethiopic`: the verse numeral (`ቍ`) if present on this row
   - `amharic_title`: the corresponding Amharic translation on the right (e.g., `የልደቱ መጽሐፍ ።` or `የኢየሱስ ክርስቶስን የትውልዱን ታሪክና ቍጥር ስለ መንገር ።`)
2. In `columns`, also provide the exact line-by-line diplomatic transcription of the Left side (`column_index=1`, including the `ም` and `ቍ` markers) and Right side (`column_index=2`).
3. Preserve all Fidels and Ethiopic numerals (`፩`..`፳፰`, `፴`, `፵`...) with 100% accuracy.
"""

PROMPT_ILLUSTRATION = """You are an expert in Ethiopian Orthodox iconography and Classical Ge'ez (ግዕዝ).
Transcribe PDF Page 187 (Book Page ፫፻፮ / 306), which is the full-page Crucifixion illustration plate.
1. Extract the cross titulus inscription (`title_inscription`).
2. In `caption_lines`, transcribe the 2-line Ge'ez prayer at the bottom of the illustration character-for-character (preserving every `፡` and Fidel).
3. Provide a brief description of the illustration in `description`.
"""

async def extract_single_page(client: genai.Client, pdf_page: int, sem: asyncio.Semaphore, force: bool = False):
    out_path = os.path.join(PAGES_DIR, f"page_{pdf_page:03d}.json")
    if os.path.exists(out_path) and not force:
        return {"pdf_page": pdf_page, "status": "cached"}

    book_num = get_book_page_number(pdf_page)
    book_eth = int_to_ethiopic(book_num) if book_num else None

    # Handle blank pages deterministically
    if pdf_page in (188, 194, 201):
        payload = {
            "pdf_page": pdf_page,
            "book_page_arabic": book_num,
            "book_page_ethiopic": book_eth,
            "page_type": "blank",
            "running_header": "",
            "columns": [],
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"Page {pdf_page:3d}: BLANK saved.")
        return payload

    async with sem:
        for attempt in range(4):
            try:
                t0 = time.time()
                if pdf_page == 187:
                    img_bgr = cv2.imread(f"data/raw_images/page_{pdf_page:03d}.jpg")
                    h, w, _ = img_bgr.shape
                    bot_crop = cv2.resize(img_bgr[int(h*0.65):int(h*0.85), int(w*0.20):int(w*0.75)], (0, 0), fx=3.0, fy=3.0, interpolation=cv2.INTER_LANCZOS4)
                    full_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
                    bot_pil = Image.fromarray(cv2.cvtColor(bot_crop, cv2.COLOR_BGR2RGB))
                    resp = await client.aio.models.generate_content(
                        model="gemini-4-argon",
                        contents=[full_pil, bot_pil, PROMPT_ILLUSTRATION],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=IllustrationPageTranscription,
                            temperature=0.0,
                        ),
                    )
                    parsed = json.loads(resp.text)
                    payload = {
                        "pdf_page": pdf_page,
                        "book_page_arabic": book_num,
                        "book_page_ethiopic": book_eth,
                        "page_type": "illustration",
                        "running_header": book_eth or "",
                        "illustration": parsed,
                        "columns": [
                            {
                                "column_index": 1,
                                "lines": parsed.get("caption_lines", []),
                            }
                        ],
                    }
                elif pdf_page == 193 or (195 <= pdf_page <= 200):
                    full_pil, top_pil, bot_pil = prepare_toc_crops(pdf_page)
                    prompt = PROMPT_TOC.format(pdf_page=pdf_page, book_page_eth=book_eth, book_page_num=book_num)
                    resp = await client.aio.models.generate_content(
                        model="gemini-4-argon",
                        contents=[full_pil, top_pil, bot_pil, prompt],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=TocPageTranscription,
                            temperature=0.0,
                        ),
                    )
                    parsed = json.loads(resp.text)
                    payload = {
                        "pdf_page": pdf_page,
                        "book_page_arabic": book_num,
                        "book_page_ethiopic": book_eth,
                        "page_type": "chapter_index" if pdf_page == 193 else "topical_index",
                        "running_header": f"{parsed.get('running_header_geez', '')} | {parsed.get('running_header_amharic', '')}",
                        "toc_entries": parsed.get("entries", []),
                        "columns": parsed.get("columns", []),
                    }
                else:
                    full_pil, crops, boxes = prepare_3col_crops(pdf_page)
                    prompt = PROMPT_3COL.format(pdf_page=pdf_page, book_page_eth=book_eth, book_page_num=book_num)
                    resp = await client.aio.models.generate_content(
                        model="gemini-4-argon",
                        contents=[full_pil, crops[0], crops[1], crops[2], prompt],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=PageTranscription,
                            temperature=0.0,
                        ),
                    )
                    parsed = json.loads(resp.text)
                    payload = {
                        "pdf_page": pdf_page,
                        "book_page_arabic": book_num,
                        "book_page_ethiopic": book_eth,
                        "page_type": "commentary_3col",
                        "running_header": parsed.get("running_header", ""),
                        "column_boxes": boxes,
                        "columns": parsed.get("columns", []),
                    }

                dt = time.time() - t0
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                line_counts = [len(c.get("lines", [])) for c in payload.get("columns", [])]
                print(f"✅ Page {pdf_page:3d} ({book_eth}): {dt:.1f}s | type={payload['page_type']} | lines={line_counts}", flush=True)
                return payload
            except Exception as e:
                wait = 4 * (attempt + 1)
                print(f"⚠️ Page {pdf_page:3d} attempt {attempt+1} error: {e}. Retrying in {wait}s...", flush=True)
                await asyncio.sleep(wait)
        print(f"❌ Page {pdf_page:3d} FAILED after 4 attempts!", flush=True)
        return {"pdf_page": pdf_page, "status": "failed"}

async def main():
    # Seed pages 1 and 2 from our verified benchmark if not yet in PAGES_DIR
    for p in (1, 2):
        bench_file = f"data/debug_crops/bench_p{p}_argon.json"
        out_path = os.path.join(PAGES_DIR, f"page_{p:03d}.json")
        if os.path.exists(bench_file) and not os.path.exists(out_path):
            bdata = json.load(open(bench_file, encoding="utf-8"))
            _, _, boxes = prepare_3col_crops(p)
            book_num = get_book_page_number(p)
            book_eth = int_to_ethiopic(book_num)
            payload = {
                "pdf_page": p,
                "book_page_arabic": book_num,
                "book_page_ethiopic": book_eth,
                "page_type": "commentary_3col",
                "running_header": bdata.get("running_header", ""),
                "column_boxes": boxes,
                "columns": bdata.get("columns", []),
            }
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            print(f"Seeded verified Page {p:03d} ({book_eth}) from benchmark.")

    # Parse page list or range from CLI
    if len(sys.argv) > 1:
        pages = []
        for arg in sys.argv[1:]:
            if "-" in arg:
                a, b = arg.split("-")
                pages.extend(range(int(a), int(b) + 1))
            else:
                pages.append(int(arg))
    else:
        # Prioritize TOC / Index pages first, then all pages 1..200
        toc_pages = [187, 188, 192, 193, 194, 195, 196, 197, 198, 199, 200]
        other_pages = [p for p in range(1, 201) if p not in toc_pages]
        pages = toc_pages + other_pages

    concurrency = int(os.environ.get("ARGON_CONCURRENCY", "12"))
    sem = asyncio.Semaphore(concurrency)
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    print(f"Starting Gemini 4 Argon extraction for {len(pages)} pages (concurrency={concurrency})...", flush=True)
    t0 = time.time()
    tasks = [extract_single_page(client, p, sem) for p in pages]
    await asyncio.gather(*tasks)
    print(f"🎉 Batch finished in {time.time() - t0:.1f}s!", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
