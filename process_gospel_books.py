import argparse
import asyncio
import glob
import json
import os
import re
import sqlite3
import sys
import time
from typing import Dict, List, Optional

import cv2
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel, Field

load_dotenv()

ETH_DIGIT_MAP = {
    "፩": 1, "፪": 2, "፫": 3, "፬": 4, "፭": 5, "፮": 6, "፯": 7, "፰": 8, "፱": 9,
    "፲": 10, "፳": 20, "፴": 30, "፵": 40, "፶": 50, "፷": 60, "፸": 70, "፹": 80, "፺": 90,
    "፻": 100, "፼": 10000,
}

ETHIOPIC_UNITS = ["", "፩", "፪", "፫", "፬", "፭", "፮", "፯", "፰", "፱"]
ETHIOPIC_TENS = ["", "፲", "፳", "፴", "፵", "፶", "፷", "፸", "፹", "፺"]

def int_to_ethiopic(n: Optional[int]) -> str:
    if not n or n <= 0:
        return ""
    if n >= 100:
        hundreds = n // 100
        rem = n % 100
        h_prefix = "" if hundreds == 1 else ETHIOPIC_UNITS[hundreds]
        return f"{h_prefix}፻{int_to_ethiopic(rem)}"
    tens = n // 10
    units = n % 10
    return f"{ETHIOPIC_TENS[tens]}{ETHIOPIC_UNITS[units]}"

def ethiopic_to_int(s: Optional[str]) -> Optional[int]:
    if not s:
        return None
    cleaned = "".join(ch for ch in s if ch in ETH_DIGIT_MAP)
    if not cleaned:
        return None
    total = 0
    current = 0
    for ch in cleaned:
        val = ETH_DIGIT_MAP[ch]
        if val == 100:
            if current == 0:
                current = 1
            total += current * 100
            current = 0
        elif val == 10000:
            if current == 0:
                current = 1
            total += current * 10000
            current = 0
        else:
            current += val
    total += current
    return total if total > 0 else None

BOOK_CONFIGS = {
    "markos": {
        "key": "markos",
        "title_geez": "የጌታችን የኢየሱስ ክርስቶስ ቅዱስ ወንጌል ፡ ቅዱስ ማርቆስ እንደ ጻፈው ።",
        "title_english": "The Holy Gospel of Our Lord Jesus Christ According to St. Mark — Traditional Ge'ez & Amharic Andemta Commentary (ወንጌለ ማርቆስ አንድምታ ትርጓሜ)",
        "evangelist_geez": "ማርቆስ",
        "evangelist_en": "Mark",
        "total_pages": 62,
        "max_chapters": 16,
        "raw_images_dir": "data/markos/raw_images",
        "out_dir": "data/markos/extracted",
        "pages_dir": "data/markos/extracted/pages",
        "verified_dir": "data/markos/extracted/verified_logs",
        "illustration_pages": [1],
        "blank_pages": [],
        "chapter_index_pages": [58],
        "topical_index_pages": [59, 60, 61, 62],
        "canon_table_pages": [],
        "harag_header_pages": [2],
        "short_colophon_pages": [57],
    },
    "lukas": {
        "key": "lukas",
        "title_geez": "የጌታችን የኢየሱስ ክርስቶስ ቅዱስ ወንጌል ፡ ቅዱስ ሉቃስ እንደ ጻፈው ።",
        "title_english": "The Holy Gospel of Our Lord Jesus Christ According to St. Luke — Traditional Ge'ez & Amharic Andemta Commentary (ወንጌለ ሉቃስ አንድምታ ትርጓሜ)",
        "evangelist_geez": "ሉቃስ",
        "evangelist_en": "Luke",
        "total_pages": 127,
        "max_chapters": 24,
        "raw_images_dir": "data/lukas/raw_images",
        "out_dir": "data/lukas/extracted",
        "pages_dir": "data/lukas/extracted/pages",
        "verified_dir": "data/lukas/extracted/verified_logs",
        "illustration_pages": [1],
        "blank_pages": [],
        "chapter_index_pages": [120],
        "topical_index_pages": [121, 122, 123, 124, 125, 126, 127],
        "canon_table_pages": [],
        "harag_header_pages": [2],
        "short_colophon_pages": [],
    },
    "yohannes": {
        "key": "yohannes",
        "title_geez": "የጌታችን የኢየሱስ ክርስቶስ ቅዱስ ወንጌል ። ቅዱስ ዮሐንስ እንደ ጻፈው ።",
        "title_english": "The Holy Gospel of Our Lord Jesus Christ According to St. John — Traditional Ge'ez & Amharic Andemta Commentary (ወንጌለ ዮሐንስ አንድምታ ትርጓሜ)",
        "evangelist_geez": "ዮሐንስ",
        "evangelist_en": "John",
        "total_pages": 137,
        "max_chapters": 21,
        "raw_images_dir": "data/yohannes/raw_images",
        "out_dir": "data/yohannes/extracted",
        "pages_dir": "data/yohannes/extracted/pages",
        "verified_dir": "data/yohannes/extracted/verified_logs",
        "illustration_pages": [1],
        "blank_pages": [119],
        "chapter_index_pages": [114],
        "topical_index_pages": [115, 116, 117, 118],
        "canon_table_pages": list(range(120, 138)),
        "harag_header_pages": [2],
        "short_colophon_pages": [113],
    },
}

def get_book_page_number(book_key: str, pdf_page: int) -> Optional[int]:
    if book_key == "markos":
        return 319 + pdf_page
    elif book_key == "lukas":
        return 382 + pdf_page
    elif book_key == "yohannes":
        if pdf_page == 119:
            return None
        if 1 <= pdf_page <= 118:
            return 510 + pdf_page
        if 120 <= pdf_page <= 137:
            return 509 + pdf_page
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
    text: str = Field(description="Exact line text. Wrap root Gospel Ge'ez verse words in ⟪...⟫ so root scripture is distinguished from commentary. Do NOT put ↵ in text.")
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
    geez_title: str = Field(description="Left column Ge'ez topic/chapter/canon entry")
    chapter_ethiopic: Optional[str] = Field(default=None, description="Chapter number in Ethiopic numerals (e.g. ፩, ፪) if printed on this row")
    verse_ethiopic: Optional[str] = Field(default=None, description="Verse number in Ethiopic numerals (e.g. ፩, ፲፰) if printed on this row")
    amharic_title: str = Field(description="Right column Amharic translation or canon parallel references")
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

class LineCorrection(BaseModel):
    column_index: int = Field(description="1, 2, or 3")
    line_num: int = Field(description="1-based line_num from the existing transcription")
    old_text: str = Field(description="The previous Stage-1 text of this line")
    corrected_text: str = Field(description="The corrected text of this line (preserving ⟪ and ⟫ markers around root Gospel Ge'ez words; NEVER include ↵)")
    word_wraps_to_next_line: bool = Field(description="True if the last word on this line splits mid-word onto the next line")
    visual_confusable_pair: str = Field(description="The exact visually confused characters fixed, e.g. 'ሺ -> ቢ', 'ዘርአ -> ዘርእ', 'ሖ -> ሐ'")
    reason: str = Field(description="Brief philological + visual explanation of why the ink-bleed/faded glyph was misread and how the image + Ge'ez/Amharic grammar confirms the correction")

class PageVerificationResult(BaseModel):
    corrections: List[LineCorrection] = Field(default_factory=list, description="List of lines that had OCR lookalike/ink-bleed errors and their verified corrections. Empty if all lines are 100% accurate.")
    remaining_uncertain: List[UncertainSpan] = Field(default_factory=list, description="Only genuine print/typesetting anomalies in the original physical book where the printed metal type itself has a typo.")

# --- Image Preparation ---

def prepare_3col_crops(cfg: Dict, pdf_page: int):
    img_path = os.path.join(cfg["raw_images_dir"], f"page_{pdf_page:03d}.jpg")
    img_bgr = cv2.imread(img_path)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    is_short = pdf_page in cfg["short_colophon_pages"]
    roi_y0 = int(h * 0.28) if pdf_page in cfg["harag_header_pages"] else int(h * 0.18)
    roi_y1 = int(h * 0.45) if is_short else int(h * 0.85)
    roi = gray[roi_y0:roi_y1, :]
    _, bw = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    col_proj = np.sum(bw, axis=0) / 255.0
    smooth = np.convolve(col_proj, np.ones(15) / 15.0, mode="same")
    g1 = int(w * 0.28) + int(np.argmin(smooth[int(w * 0.28):int(w * 0.44)]))
    g2 = int(w * 0.56) + int(np.argmin(smooth[int(w * 0.56):int(w * 0.72)]))

    y0 = int(h * 0.20) if pdf_page in cfg["harag_header_pages"] else int(h * 0.05)
    y1 = int(h * 0.55) if is_short else h

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

def prepare_toc_crops(cfg: Dict, pdf_page: int):
    img_path = os.path.join(cfg["raw_images_dir"], f"page_{pdf_page:03d}.jpg")
    img_bgr = cv2.imread(img_path)
    h, w, _ = img_bgr.shape
    top_band = img_bgr[int(h * 0.04):int(h * 0.55), :]
    bot_band = img_bgr[int(h * 0.48):h, :]
    up_top = cv2.resize(top_band, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_LANCZOS4)
    up_bot = cv2.resize(bot_band, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_LANCZOS4)
    full_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    return full_pil, Image.fromarray(cv2.cvtColor(up_top, cv2.COLOR_BGR2RGB)), Image.fromarray(cv2.cvtColor(up_bot, cv2.COLOR_BGR2RGB))

PROMPT_3COL = """You are the world's foremost Ethiopian Orthodox Yeneta (ሊቀ ሊቃውንት) and philologist in Classical Ethiopic (Ge'ez / ልሳነ ግዕዝ) and Amharic Andemta Commentary (ወንጌለ {evangelist_geez} አንድምታ ትርጓሜ — Gospel of {evangelist_en}).
Transcribe PDF Page {pdf_page} (Book Page {book_page_eth} / {book_page_num}) with 100% character-level fidelity.

Images provided:
1. Full page image
2. Column 1 (left) 2x zoom including left margin
3. Column 2 (middle) 2x zoom including left margin
4. Column 3 (right) 2x zoom including left margin

STRICT PHILOLOGICAL & VISUAL RULES:
1. Transcribe EVERY physical line of Column 1, Column 2, and Column 3 in exact top-to-bottom order. Never skip or merge lines.
2. Preserve exact Ethiopic Fidels (ሀ/ሐ/ኀ, ሰ/ሠ, አ/ዐ, ጸ/ፀ, ቍ/ቁ, ኵ/ኩ) and exact punctuation (፡, ።, ፤, ፥). Do NOT modernize archaic Andemta forms (keep ሁነው, ለኒህ, ደንጊያ, ኖሎት, አባግዕ, ፩ዱ, etc. exactly as printed).
3. GUARD AGAINST LEAD-TYPE INK BLEED LOOKALIKES:
   - Watch out for top-serif ink bleed making `ቢ` look like `ሺ` or `ቨ` (e.g. `ቢያነሱላቸው`, `ቢሉ`), or `በ` vs `ባ`, `ሂ` vs `ሄ`, `ሐ` vs `ሖ`, `አ` vs `እ`, `ን` vs `ሩ`, `ግ` vs `ም`, `፷` vs `፰`.
   - Always mentally rejoin words split across lines (`word_wraps_to_next_line = true`) to verify that both Classical Ge'ez (`ልሳነ ግዕዝ`) morphology and Amharic (`አማርኛ`) words are 100% real, grammatical words matching the Gospel of {evangelist_en}.
   - Output ONLY pure Ethiopic Fidels, punctuation, and `⟪...⟫` markers (never output non-Ethiopic characters or `↵`).
4. Wrap the root Gospel of {evangelist_en} Ge'ez verse words/phrases in ⟪...⟫. Do NOT wrap patristic/other biblical citations or Amharic commentary in ⟪...⟫ unless it is the root Gospel of {evangelist_en} verse lemma being commented on.
5. Set `line_type` to:
   - `"chapter_title"` for major chapter headings like `ምዕራፍ ፩ ።`, `ምዕራፍ ፪ ።`
   - `"section_title"` for pericope subheadings like `በእንተ ስብከተ ዮሐንስ ።`
   - `"colophon"` for concluding colophon lines at the end of the book
   - `"body"` for all standard verse, prologue, and commentary lines
6. Record any Ethiopic verse numeral printed in the left margin of a line in `margin_tag` (e.g. `"፩"`, `"፪"`, `"፳፭"`).
7. Set `word_wraps_to_next_line = true` whenever the last word of a line splits mid-word onto the next line.
"""

PROMPT_TOC = """You are the world's foremost philologist in Classical Ethiopic (Ge'ez / ግዕዝ) and Ethiopian Orthodox Andemta Commentary (ወንጌለ {evangelist_geez} አንድምታ ትርጓሜ).
Transcribe this Index / Canon Table page (PDF Page {pdf_page}, Book Page {book_page_eth} / {book_page_num}) with 100% character-level fidelity.

Images provided:
1. Full page image
2. Top half 2x zoom
3. Bottom half 2x zoom

RULES:
1. In `entries`, extract every row of the table in top-to-bottom order:
   - `geez_title`: the Ge'ez entry or canon phrase
   - `chapter_ethiopic`: the chapter numeral (`ም`) if present on this row
   - `verse_ethiopic`: the verse numeral (`ቍ`) if present on this row
   - `amharic_title`: the corresponding Amharic translation on the right (or parallel Gospel references if this is a Canon Table `ሰንጠረዥ`)
2. In `columns`, also provide the exact line-by-line diplomatic transcription of the Left side (`column_index=1`) and Right side (`column_index=2`).
3. Preserve all Fidels and Ethiopic numerals (`፩`..`፺`, `፻`) with 100% accuracy.
"""

PROMPT_ILLUSTRATION = """You are an expert in Ethiopian Orthodox iconography and Classical Ge'ez (ግዕዝ).
Transcribe PDF Page {pdf_page} (Book Page {book_page_eth} / {book_page_num}), which is the full-page Evangelist portrait plate of St. {evangelist_en} ({evangelist_geez}).
1. Extract the banner/ribbon inscription (`title_inscription`, e.g., `ቅ ፡ ማርቆስ ።`, `ቅዱስ ሉቃስ`, `ቅዱስ ዮሐንስ`).
2. In `caption_lines`, transcribe any caption or inscription lines.
3. Provide a brief description of the traditional woodcut illustration in `description`.
"""

async def extract_single_page(client: genai.Client, cfg: Dict, pdf_page: int, sem: asyncio.Semaphore, force: bool = False):
    out_path = os.path.join(cfg["pages_dir"], f"page_{pdf_page:03d}.json")
    if os.path.exists(out_path) and not force:
        return {"pdf_page": pdf_page, "status": "cached"}

    book_num = get_book_page_number(cfg["key"], pdf_page)
    book_eth = int_to_ethiopic(book_num) if book_num else None

    if pdf_page in cfg["blank_pages"]:
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
        print(f"[{cfg['key']}] Page {pdf_page:3d}: BLANK saved.")
        return payload

    async with sem:
        for attempt in range(20):
            try:
                t0 = time.time()
                if pdf_page in cfg["illustration_pages"]:
                    img_path = os.path.join(cfg["raw_images_dir"], f"page_{pdf_page:03d}.jpg")
                    img_bgr = cv2.imread(img_path)
                    full_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
                    prompt = PROMPT_ILLUSTRATION.format(
                        pdf_page=pdf_page,
                        book_page_eth=book_eth,
                        book_page_num=book_num,
                        evangelist_en=cfg["evangelist_en"],
                        evangelist_geez=cfg["evangelist_geez"],
                    )
                    resp = await client.aio.models.generate_content(
                        model="gemini-4-argon",
                        contents=[full_pil, prompt],
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
                elif (
                    pdf_page in cfg["chapter_index_pages"]
                    or pdf_page in cfg["topical_index_pages"]
                    or pdf_page in cfg["canon_table_pages"]
                ):
                    full_pil, top_pil, bot_pil = prepare_toc_crops(cfg, pdf_page)
                    prompt = PROMPT_TOC.format(
                        pdf_page=pdf_page,
                        book_page_eth=book_eth,
                        book_page_num=book_num,
                        evangelist_geez=cfg["evangelist_geez"],
                    )
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
                    if pdf_page in cfg["chapter_index_pages"]:
                        p_type = "chapter_index"
                    elif pdf_page in cfg["topical_index_pages"]:
                        p_type = "topical_index"
                    else:
                        p_type = "canon_table"
                    payload = {
                        "pdf_page": pdf_page,
                        "book_page_arabic": book_num,
                        "book_page_ethiopic": book_eth,
                        "page_type": p_type,
                        "running_header": f"{parsed.get('running_header_geez', '')} | {parsed.get('running_header_amharic', '')}",
                        "toc_entries": parsed.get("entries", []),
                        "columns": parsed.get("columns", []),
                    }
                else:
                    full_pil, crops, boxes = prepare_3col_crops(cfg, pdf_page)
                    prompt = PROMPT_3COL.format(
                        pdf_page=pdf_page,
                        book_page_eth=book_eth,
                        book_page_num=book_num,
                        evangelist_geez=cfg["evangelist_geez"],
                        evangelist_en=cfg["evangelist_en"],
                    )
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
                    for col in parsed.get("columns", []):
                        for ln in col.get("lines", []):
                            ln["text"] = ln.get("text", "").replace("↵", "").rstrip()
                    payload = {
                        "pdf_page": pdf_page,
                        "book_page_arabic": book_num,
                        "book_page_ethiopic": book_eth,
                        "page_type": "commentary_3col",
                        "running_header": parsed.get("running_header", ""),
                        "column_boxes": boxes,
                        "columns": parsed.get("columns", []),
                    }

                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)

                dt = time.time() - t0
                n_lines = sum(len(c.get("lines", [])) for c in payload.get("columns", []))
                print(f"[{cfg['key']}] Stage-1 Page {pdf_page:3d} (Book {book_eth}): {payload['page_type']} -> {n_lines} lines in {dt:.1f}s", flush=True)
                return payload
            except Exception as e:
                err_s = str(e)
                wait_s = (15.0 + 5.0 * attempt) if ("429" in err_s or "RESOURCE_EXHAUSTED" in err_s) else (3.0 * (attempt + 1))
                print(f"[{cfg['key']}] Stage-1 Page {pdf_page:3d} attempt {attempt+1} error (sleeping {wait_s:.0f}s): {e}", flush=True)
                await asyncio.sleep(wait_s)

        raise RuntimeError(f"[{cfg['key']}] Failed to extract page {pdf_page}")

# --- Stage 2 Verification ---

def build_rejoined_preview(p_data: Dict, prev_tail: str = "", next_head: str = "") -> str:
    out = []
    if prev_tail:
        out.append(f"[PREV PAGE END]: ... {prev_tail}")
    for col in p_data.get("columns", []):
        c_idx = col.get("column_index", 1)
        out.append(f"\n=== COLUMN {c_idx} ===")
        lines = col.get("lines", [])
        for ln in lines:
            lnum = ln.get("line_num", 0)
            mtag = f" m={ln['margin_tag']}" if ln.get("margin_tag") else ""
            txt = ln.get("text", "")
            wraps = "↵" if ln.get("word_wraps_to_next_line") else ""
            out.append(f"[Col {c_idx} L{lnum:02d}{mtag}] {txt}{wraps}")

        rejoined_tokens = []
        curr_buf = ""
        for ln in lines:
            lnum = ln.get("line_num", 0)
            txt = ln.get("text", "").replace("⟪", "").replace("⟫", "").strip()
            if curr_buf:
                curr_buf += f"↵[L{lnum:02d}]" + txt
            else:
                curr_buf = f"[L{lnum:02d}] " + txt
            if not ln.get("word_wraps_to_next_line"):
                rejoined_tokens.append(curr_buf)
                curr_buf = ""
        if curr_buf:
            rejoined_tokens.append(curr_buf)
        out.append(f"--- Column {c_idx} Rejoined Word Stream ---")
        out.append(" ".join(rejoined_tokens))

    if next_head:
        out.append(f"\n[NEXT PAGE START]: {next_head} ...")
    return "\n".join(out)

VERIFY_PROMPT = """You are the world's foremost Ethiopian Orthodox Yeneta (ሊቀ ሊቃውንት) and Philologist of Classical Ge'ez (ልሳነ ግዕዝ) and Amharic Andemta Commentary (ወንጌለ {evangelist_geez} አንድምታ ትርጓሜ — Gospel of {evangelist_en}).

We are performing Stage-2 Philological & Visual Verification on PDF Page {pdf_page} (Book Page {book_page_eth}).
In Stage 1, an OCR pass transcribed each line in isolation. Because this old lead-type printing has ink bleed, uneven serif pressure, and mid-word line wraps (`↵`), Stage 1 occasionally misread visually confusable Fidels.

YOUR TASK:
Inspect the provided 2x zoomed column images AND read the Rejoined Word Stream carefully word-by-word in both **Classical Ge'ez (ልሳነ ግዕዝ)** and **Amharic (አማርኛ)**.
Find and fix EVERY single word where Stage 1 misread a visually similar Fidel or numeral.

CRITICAL RULES FOR GE'EZ (ልሳነ ግዕዝ) VERIFICATION:
1. **Root Gospel of {evangelist_en} Quotes (`⟪...⟫`) & Patristic Citations (`እንዲል`)**:
   - Verify every Ge'ez word against canonical Ge'ez Gospel of {evangelist_en} phrasing and Classical Ge'ez morphology (construct states `-አ`/`-ተ`, pronominal suffixes `-ሁ`/`-ሆሙ`/`-ክሙ`/`-ከ`, subjunctive/gerundive endings, accusative markers, prepositions `ውስተ`, `እምኀበ`, `በእንተ`).
   - Watch for ink-bleed confusables in Ge'ez:
     - 1st order (`ግዕዝ`) vs 4th order (`ራብዕ`) vs 6th order (`ሳድስ`): e.g. `ዘርእከ` vs `ዘርአከ`, `ለእግዚእነ` vs `ለአግዚአነ`, `ሐዊረክሙ` vs `ሖዊረክሙ`.
     - Visually similar base characters: `ሀ/ሐ/ኀ`, `ሰ/ሠ`, `አ/ዐ`, `ጸ/ፀ`, `በ/ለ/ሊ`, `ተ/ቶ/ት`, `ነ/ኒ/ና`, `ወ/ዐ`, `ደ/ድ/ዳ`, `ገ/ግ/ጎ`, `ፈ/ፍ/ፎ`, `ይ/ደ`.
     - Ethiopic numerals: `፷` (60) vs `፰` (8), `፸` (70) vs `፯` (7), `፳` (20) vs `፺` (90), `፴` (30) vs `፫` (3).

CRITICAL RULES FOR AMHARIC (አማርኛ) ANDEMTA VERIFICATION:
2. **Continuous Word Sense Across Line Wraps (`↵`)**:
   - Join split words across `↵` and across column boundaries (`Col 1 last line -> Col 2 L01`, `Col 2 last line -> Col 3 L01`) and verify the complete word makes 100% grammatical and theological sense in the Andemta commentary.
   - Watch for ink-bleed confusables in Amharic:
     - Top-bar/serif ink bleed: `ቢ` misread as `ሺ` or `ቨ` (e.g., `ቢያነሱላቸው` misread as `ሺያነሱላቸው`).
     - Ring/loop ink bleed: `መ/ሙ/ሚ` vs `ሥ/ሡ`, `በ/ቡ/ቢ/ባ` vs `ለ/ሉ/ሊ/ላ`, `ቀ/ቆ` vs `ተ/ቶ`, `ከ/ኩ/ኪ` vs `ነ/ኑ/ኒ`, `ገ/ጉ/ጊ` vs `ነ/ኑ/ኒ`, `ኀ/ኃ` vs `ነ/ና`, `ዐ/ዓ` vs `ዋ`, `ዘ/ዙ` vs `ዠ/ዡ`, `ጠ/ጡ/ጢ` vs `ጨ/ጩ/ጪ`.
     - NEVER output non-Ethiopic script characters (such as Hebrew or Arabic letters) or `↵` inside `corrected_text`.

STRICT NON-HALLUCINATION / ARCHAIC PRESERVATION RULE:
3. **DO NOT modernize authentic archaic Andemta forms** that are genuinely printed in the book:
   - Keep `ሁነው` (do not change to `ሆነው`), keep `ለኒህ` / `እኒህ` (do not change to `ለነዚህ`), keep `ደንጊያ` (do not change to `ድንጋይ`), keep `ኖሎት`, `አባግዕ`, `፩ዱ`, `፫ቱ`, `አንቅተው`, `አውጭ`, `ይሻሉ`.
4. **Visual Grounding**:
   - Every correction you return in `corrections` MUST correspond to what is actually printed on the page image (where Stage 1 misread a stroke, vowel ring, leg, or split word). Do NOT invent words that do not match the visual glyphs on the page.

Here is the Stage-1 Transcription and Rejoined Word Stream for PDF Page {pdf_page}:
{preview_text}
"""

def clean_ethiopic_text(txt: str) -> str:
    txt = txt.replace("↵", "").rstrip()
    txt = re.sub(r"^\([፩-፼ወ]+\)\s*", "", txt)
    # Replace Hebrew Nun if ever emitted by token glitch with Ethiopic ን
    txt = txt.replace("נ", "ን").replace("ئ", "እ")
    return txt

async def verify_single_page(client: genai.Client, cfg: Dict, pdf_page: int, all_pages: Dict[int, Dict], sem: asyncio.Semaphore, force: bool = False):
    verify_log_path = os.path.join(cfg["verified_dir"], f"verify_{pdf_page:03d}.json")
    page_path = os.path.join(cfg["pages_dir"], f"page_{pdf_page:03d}.json")

    if not os.path.exists(page_path):
        return {"pdf_page": pdf_page, "status": "missing"}

    p_data = all_pages[pdf_page]
    if p_data.get("page_type") in ("blank", "illustration"):
        return {"pdf_page": pdf_page, "status": "skipped_non_text", "corrections": 0}

    if os.path.exists(verify_log_path) and not force:
        vlog = json.load(open(verify_log_path, encoding="utf-8"))
        return {"pdf_page": pdf_page, "status": "cached", "corrections": len(vlog.get("corrections", []))}

    prev_tail = ""
    if (pdf_page - 1) in all_pages and all_pages[pdf_page - 1].get("columns"):
        prev_cols = all_pages[pdf_page - 1]["columns"]
        if prev_cols and prev_cols[-1].get("lines"):
            last_lines = prev_cols[-1]["lines"][-2:]
            prev_tail = " ".join(l.get("text", "") for l in last_lines)

    next_head = ""
    if (pdf_page + 1) in all_pages and all_pages[pdf_page + 1].get("columns"):
        next_cols = all_pages[pdf_page + 1]["columns"]
        if next_cols and next_cols[0].get("lines"):
            first_lines = next_cols[0]["lines"][:2]
            next_head = " ".join(l.get("text", "") for l in first_lines)

    preview_text = build_rejoined_preview(p_data, prev_tail, next_head)
    book_eth = p_data.get("book_page_ethiopic") or str(pdf_page)

    async with sem:
        for attempt in range(20):
            try:
                t0 = time.time()
                if p_data.get("page_type") == "commentary_3col":
                    full_pil, crops, _ = prepare_3col_crops(cfg, pdf_page)
                    contents = [
                        full_pil,
                        crops[0],
                        crops[1],
                        crops[2],
                        VERIFY_PROMPT.format(
                            pdf_page=pdf_page,
                            book_page_eth=book_eth,
                            evangelist_geez=cfg["evangelist_geez"],
                            evangelist_en=cfg["evangelist_en"],
                            preview_text=preview_text,
                        ),
                    ]
                else:
                    full_pil, top_pil, bot_pil = prepare_toc_crops(cfg, pdf_page)
                    contents = [
                        full_pil,
                        top_pil,
                        bot_pil,
                        VERIFY_PROMPT.format(
                            pdf_page=pdf_page,
                            book_page_eth=book_eth,
                            evangelist_geez=cfg["evangelist_geez"],
                            evangelist_en=cfg["evangelist_en"],
                            preview_text=preview_text,
                        ),
                    ]

                resp = await client.aio.models.generate_content(
                    model="gemini-4-argon",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=PageVerificationResult,
                        temperature=0.0,
                    ),
                )
                res_json = json.loads(resp.text)
                corrections = res_json.get("corrections", [])

                applied = 0
                for c in corrections:
                    c_idx = c["column_index"]
                    l_num = c["line_num"]
                    new_txt = clean_ethiopic_text(c["corrected_text"])
                    c["corrected_text"] = new_txt
                    for col in p_data.get("columns", []):
                        if col.get("column_index") == c_idx:
                            for ln in col.get("lines", []):
                                if ln.get("line_num") == l_num:
                                    old_clean = clean_ethiopic_text(ln.get("text", ""))
                                    if old_clean != new_txt:
                                        ln["stage1_text"] = old_clean
                                        ln["text"] = new_txt
                                        ln["word_wraps_to_next_line"] = c["word_wraps_to_next_line"]
                                        ln["stage2_correction"] = {
                                            "pair": c["visual_confusable_pair"],
                                            "reason": c["reason"],
                                        }
                                        applied += 1
                                    ln["uncertain"] = []

                for col in p_data.get("columns", []):
                    for ln in col.get("lines", []):
                        ln["text"] = clean_ethiopic_text(ln.get("text", ""))
                        if ln.get("uncertain"):
                            ln["uncertain"] = [
                                u for u in ln["uncertain"]
                                if "typo" in u.get("note", "").lower() or "omitted" in u.get("note", "").lower()
                            ]

                p_data["stage2_verified"] = True
                p_data["stage2_corrections_count"] = applied

                with open(page_path, "w", encoding="utf-8") as f:
                    json.dump(p_data, f, ensure_ascii=False, indent=2)

                dt = time.time() - t0
                log_payload = {
                    "pdf_page": pdf_page,
                    "book_page_ethiopic": book_eth,
                    "elapsed_sec": round(dt, 1),
                    "applied_count": applied,
                    "corrections": corrections,
                }
                with open(verify_log_path, "w", encoding="utf-8") as f:
                    json.dump(log_payload, f, ensure_ascii=False, indent=2)

                print(f"[{cfg['key']}] Stage-2 Verified Page {pdf_page:3d} ({book_eth}): {applied} lines corrected in {dt:.1f}s", flush=True)
                return {"pdf_page": pdf_page, "status": "verified", "corrections": applied}

            except Exception as e:
                err_s = str(e)
                wait_s = (15.0 + 5.0 * attempt) if ("429" in err_s or "RESOURCE_EXHAUSTED" in err_s) else (3.0 * (attempt + 1))
                print(f"[{cfg['key']}] Stage-2 Page {pdf_page:3d} attempt {attempt+1} error (sleeping {wait_s:.0f}s): {e}", flush=True)
                await asyncio.sleep(wait_s)

        raise RuntimeError(f"[{cfg['key']}] Failed Stage-2 verification on page {pdf_page}")

# --- Compilation ---

CHAPTER_RE = re.compile(r"ምዕራፍ?[\s፡፥፤።]*([፩-፼ወ]+)")

def rejoin_lines_text(lines: List[Dict]) -> str:
    if not lines:
        return ""
    parts = []
    for i, ln in enumerate(lines):
        txt = ln.get("text", "").replace("↵", "").strip()
        if not txt:
            continue
        if i == 0:
            parts.append(txt)
        else:
            prev_wraps = lines[i - 1].get("word_wraps_to_next_line", False)
            if prev_wraps:
                if parts and parts[-1].endswith("⟫") and txt.startswith("⟪"):
                    parts[-1] = parts[-1][:-1] + txt[1:]
                else:
                    parts[-1] = parts[-1] + txt
            else:
                parts.append(txt)
    return " ".join(parts)

def compile_book_data(cfg: Dict):
    pages_dir = cfg["pages_dir"]
    out_dir = cfg["out_dir"]
    os.makedirs(out_dir, exist_ok=True)

    page_files = sorted(glob.glob(os.path.join(pages_dir, "page_*.json")))
    pages_by_num: Dict[int, Dict] = {}
    for pf in page_files:
        data = json.load(open(pf, encoding="utf-8"))
        pages_by_num[data["pdf_page"]] = data

    max_ch = cfg["max_chapters"]

    # 1. Chapter Index
    chapter_index = []
    for p in cfg["chapter_index_pages"]:
        if p in pages_by_num:
            for entry in pages_by_num[p].get("toc_entries", []):
                ch_eth = entry.get("chapter_ethiopic") or ""
                ch_num = ethiopic_to_int(ch_eth) or entry.get("row_num")
                chapter_index.append({
                    "chapter_num": ch_num,
                    "chapter_ethiopic": int_to_ethiopic(ch_num),
                    "geez_incipit": entry.get("geez_title", ""),
                    "amharic_incipit": entry.get("amharic_title", ""),
                })

    # 2. Topical Index
    topical_index = []
    curr_toc_ch_eth = "፩"
    curr_toc_ch_num = 1
    for p in cfg["topical_index_pages"]:
        if p not in pages_by_num:
            continue
        p_data = pages_by_num[p]
        for entry in p_data.get("toc_entries", []):
            raw_ch = entry.get("chapter_ethiopic")
            if raw_ch:
                parsed_ch = ethiopic_to_int(raw_ch)
                if parsed_ch and 1 <= parsed_ch <= max_ch:
                    curr_toc_ch_num = parsed_ch
                    curr_toc_ch_eth = int_to_ethiopic(parsed_ch)
            raw_v = entry.get("verse_ethiopic")
            v_num = ethiopic_to_int(raw_v) if raw_v else 1
            topical_index.append({
                "topic_id": len(topical_index) + 1,
                "pdf_page": p,
                "book_page_ethiopic": p_data.get("book_page_ethiopic"),
                "chapter_num": curr_toc_ch_num,
                "chapter_ethiopic": curr_toc_ch_eth,
                "verse_num": v_num or 1,
                "verse_ethiopic": raw_v or "፩",
                "geez_title": entry.get("geez_title", ""),
                "amharic_title": entry.get("amharic_title", ""),
            })

    # 3. Canon Tables (for Yohannes)
    canon_tables = []
    for p in cfg.get("canon_table_pages", []):
        if p in pages_by_num:
            p_data = pages_by_num[p]
            canon_tables.append({
                "pdf_page": p,
                "book_page_ethiopic": p_data.get("book_page_ethiopic"),
                "running_header": p_data.get("running_header", ""),
                "entries": p_data.get("toc_entries", []),
            })

    # 4. Walk Commentary Pages
    chapters_map: Dict[int, Dict] = {}
    all_uncertain: List[Dict] = []
    all_stage2_corrections: List[Dict] = []
    total_lines_count = 0

    curr_ch_num = 1
    curr_ch_eth = "፩"
    # Start in Prologue (verse 0 = መቅድም) until ምዕራፍ ፩ is encountered
    seen_ch1_header = False
    curr_v_num = 0
    curr_v_eth = "መቅድም"
    curr_section_title: Optional[str] = "መቅድም — ብሥራተ ወንጌላዊ"

    def ensure_chapter(ch_num: int):
        if ch_num not in chapters_map:
            ch_meta = next((c for c in chapter_index if c["chapter_num"] == ch_num), None)
            chapters_map[ch_num] = {
                "chapter_num": ch_num,
                "chapter_ethiopic": int_to_ethiopic(ch_num),
                "title_geez": f"ምዕራፍ {int_to_ethiopic(ch_num)} ።",
                "geez_incipit": ch_meta["geez_incipit"] if ch_meta else "",
                "amharic_incipit": ch_meta["amharic_incipit"] if ch_meta else "",
                "start_pdf_page": None,
                "start_book_page_ethiopic": None,
                "verses_map": {},
            }
        return chapters_map[ch_num]

    def ensure_verse(ch_num: int, v_num: int, v_eth: str, pdf_page: int, book_eth: str, sec_title: Optional[str]):
        ch_obj = ensure_chapter(ch_num)
        if ch_obj["start_pdf_page"] is None:
            ch_obj["start_pdf_page"] = pdf_page
            ch_obj["start_book_page_ethiopic"] = book_eth
        v_map = ch_obj["verses_map"]
        if v_num not in v_map:
            v_map[v_num] = {
                "chapter_num": ch_num,
                "chapter_ethiopic": int_to_ethiopic(ch_num),
                "verse_num": v_num,
                "verse_ethiopic": v_eth or int_to_ethiopic(v_num) or "መቅድም",
                "section_title": sec_title,
                "start_pdf_page": pdf_page,
                "start_book_page_ethiopic": book_eth,
                "lines": [],
            }
        return v_map[v_num]

    for p in sorted(pages_by_num.keys()):
        p_data = pages_by_num[p]
        p_type = p_data.get("page_type", "")
        book_eth = p_data.get("book_page_ethiopic") or ""
        book_num = p_data.get("book_page_arabic")

        for col in p_data.get("columns", []):
            c_idx = col.get("column_index", 1)
            for ln in col.get("lines", []):
                total_lines_count += 1
                if ln.get("stage2_correction"):
                    sc = ln["stage2_correction"]
                    all_stage2_corrections.append({
                        "id": len(all_stage2_corrections) + 1,
                        "pdf_page": p,
                        "book_page_ethiopic": book_eth,
                        "book_page_arabic": book_num,
                        "column_index": c_idx,
                        "line_num": ln.get("line_num"),
                        "stage1_text": ln.get("stage1_text", ""),
                        "corrected_text": ln.get("text", ""),
                        "pair": sc.get("pair", ""),
                        "reason": sc.get("reason", ""),
                    })
                for u in (ln.get("uncertain") or []):
                    all_uncertain.append({
                        "id": len(all_uncertain) + 1,
                        "pdf_page": p,
                        "book_page_ethiopic": book_eth,
                        "book_page_arabic": book_num,
                        "column_index": c_idx,
                        "line_num": ln.get("line_num"),
                        "line_text": ln.get("text", ""),
                        "printed_text": u.get("printed_text", ""),
                        "alternative": u.get("alternative", ""),
                        "note": u.get("note", ""),
                    })

        if p_type != "commentary_3col":
            continue

        for col in p_data.get("columns", []):
            c_idx = col.get("column_index", 1)
            for ln in col.get("lines", []):
                l_num = ln.get("line_num", 1)
                l_type = ln.get("line_type", "body")
                txt = ln.get("text", "").replace("↵", "").strip()
                m_tag = ln.get("margin_tag")
                clean_txt = txt.replace("⟪", "").replace("⟫", "").strip()

                ch_match = CHAPTER_RE.search(clean_txt)
                if (l_type == "chapter_title" or (ch_match and len(clean_txt) <= 18)) and ch_match:
                    new_ch = ethiopic_to_int(ch_match.group(1))
                    if new_ch and 1 <= new_ch <= max_ch:
                        seen_ch1_header = True
                        curr_ch_num = new_ch
                        curr_ch_eth = int_to_ethiopic(new_ch)
                        curr_v_num = 1
                        curr_v_eth = "፩"
                        ch_obj = ensure_chapter(curr_ch_num)
                        ch_obj["title_geez"] = clean_txt
                        ch_obj["start_pdf_page"] = p
                        ch_obj["start_book_page_ethiopic"] = book_eth
                        continue

                if l_type == "section_title":
                    curr_section_title = clean_txt

                if m_tag and seen_ch1_header:
                    m_clean = m_tag.strip()
                    if not m_clean.startswith("ም"):
                        parsed_v = ethiopic_to_int(m_clean)
                        if parsed_v and 1 <= parsed_v <= 90:
                            if (
                                parsed_v == curr_v_num
                                or parsed_v == curr_v_num + 1
                                or (parsed_v > curr_v_num and parsed_v <= curr_v_num + 5)
                                or (curr_v_num <= 2 and parsed_v <= 5)
                            ):
                                curr_v_num = parsed_v
                                curr_v_eth = int_to_ethiopic(parsed_v)

                v_obj = ensure_verse(curr_ch_num, curr_v_num, curr_v_eth, p, book_eth, curr_section_title)
                if curr_section_title and not v_obj.get("section_title"):
                    v_obj["section_title"] = curr_section_title

                v_obj["lines"].append({
                    "pdf_page": p,
                    "book_page_ethiopic": book_eth,
                    "book_page_arabic": book_num,
                    "column_index": c_idx,
                    "line_num": l_num,
                    "margin_tag": m_tag,
                    "line_type": l_type,
                    "text": txt,
                    "word_wraps_to_next_line": ln.get("word_wraps_to_next_line", False),
                    "uncertain": ln.get("uncertain") or [],
                    "stage2_correction": ln.get("stage2_correction"),
                })

    chapters_list = []
    total_verses_count = 0
    for ch_num in sorted(chapters_map.keys()):
        ch_obj = chapters_map[ch_num]
        v_list = []
        for v_num in sorted(ch_obj["verses_map"].keys()):
            v_obj = ch_obj["verses_map"][v_num]
            rejoined = rejoin_lines_text(v_obj["lines"])
            geez_lemmas = [m.strip() for m in re.findall(r"⟪([^⟫]+)⟫", rejoined) if m.strip()]
            plain_rejoined = rejoined.replace("⟪", "").replace("⟫", "")
            v_obj["rejoined_marked_text"] = rejoined
            v_obj["rejoined_plain_text"] = plain_rejoined
            v_obj["geez_root_lemmas"] = geez_lemmas
            v_list.append(v_obj)
            total_verses_count += 1
        del ch_obj["verses_map"]
        ch_obj["verses"] = v_list
        chapters_list.append(ch_obj)

    bkey = cfg["key"]
    master_book = {
        "book_key": bkey,
        "title_geez": cfg["title_geez"],
        "title_english": cfg["title_english"],
        "stats": {
            "total_pdf_pages": cfg["total_pages"],
            "extracted_pages_count": len(pages_by_num),
            "total_chapters": len(chapters_list),
            "total_verses": total_verses_count,
            "total_diplomatic_lines": total_lines_count,
            "total_topical_index_entries": len(topical_index),
            "total_canon_table_pages": len(canon_tables),
            "total_stage2_corrections": len(all_stage2_corrections),
            "total_uncertain_apparatus_flags": len(all_uncertain),
        },
        "chapter_index": chapter_index,
        "topical_index": topical_index,
        "canon_tables": canon_tables,
        "chapters": chapters_list,
        "stage2_corrections": all_stage2_corrections,
        "uncertain_apparatus": all_uncertain,
    }

    master_json_path = os.path.join(out_dir, f"{bkey}_andemta_complete.json")
    with open(master_json_path, "w", encoding="utf-8") as f:
        json.dump(master_book, f, ensure_ascii=False, indent=2)

    db_path = os.path.join(out_dir, f"{bkey}_andemta.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE pages (
            pdf_page INTEGER PRIMARY KEY,
            book_page_arabic INTEGER,
            book_page_ethiopic TEXT,
            page_type TEXT,
            running_header TEXT,
            raw_json TEXT
        );
        CREATE TABLE chapters (
            chapter_num INTEGER PRIMARY KEY,
            chapter_ethiopic TEXT,
            title_geez TEXT,
            geez_incipit TEXT,
            amharic_incipit TEXT,
            start_pdf_page INTEGER,
            start_book_page_ethiopic TEXT
        );
        CREATE TABLE verses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter_num INTEGER,
            chapter_ethiopic TEXT,
            verse_num INTEGER,
            verse_ethiopic TEXT,
            section_title TEXT,
            start_pdf_page INTEGER,
            start_book_page_ethiopic TEXT,
            geez_root_text TEXT,
            rejoined_marked_text TEXT,
            rejoined_plain_text TEXT,
            lines_json TEXT
        );
        CREATE VIRTUAL TABLE verses_fts USING fts5(
            chapter_ethiopic,
            verse_ethiopic,
            geez_root_text,
            rejoined_plain_text,
            content='verses',
            content_rowid='id'
        );
        CREATE TABLE topical_index (
            topic_id INTEGER PRIMARY KEY,
            pdf_page INTEGER,
            book_page_ethiopic TEXT,
            chapter_num INTEGER,
            chapter_ethiopic TEXT,
            verse_num INTEGER,
            verse_ethiopic TEXT,
            geez_title TEXT,
            amharic_title TEXT
        );
    """)

    for p, p_data in sorted(pages_by_num.items()):
        cur.execute(
            "INSERT INTO pages VALUES (?, ?, ?, ?, ?, ?)",
            (p, p_data.get("book_page_arabic"), p_data.get("book_page_ethiopic"), p_data.get("page_type"), p_data.get("running_header"), json.dumps(p_data, ensure_ascii=False))
        )

    for ch in chapters_list:
        cur.execute(
            "INSERT INTO chapters VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ch["chapter_num"], ch["chapter_ethiopic"], ch["title_geez"], ch["geez_incipit"], ch["amharic_incipit"], ch["start_pdf_page"], ch["start_book_page_ethiopic"])
        )
        for v in ch["verses"]:
            geez_joined = " ፤ ".join(v["geez_root_lemmas"])
            cur.execute(
                """INSERT INTO verses (
                    chapter_num, chapter_ethiopic, verse_num, verse_ethiopic,
                    section_title, start_pdf_page, start_book_page_ethiopic,
                    geez_root_text, rejoined_marked_text, rejoined_plain_text, lines_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    v["chapter_num"], v["chapter_ethiopic"], v["verse_num"], v["verse_ethiopic"],
                    v["section_title"], v["start_pdf_page"], v["start_book_page_ethiopic"],
                    geez_joined, v["rejoined_marked_text"], v["rejoined_plain_text"],
                    json.dumps(v["lines"], ensure_ascii=False)
                )
            )
            rowid = cur.lastrowid
            cur.execute(
                "INSERT INTO verses_fts(rowid, chapter_ethiopic, verse_ethiopic, geez_root_text, rejoined_plain_text) VALUES (?, ?, ?, ?, ?)",
                (rowid, v["chapter_ethiopic"], v["verse_ethiopic"], geez_joined, v["rejoined_plain_text"])
            )

    for t in topical_index:
        cur.execute(
            "INSERT INTO topical_index VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (t["topic_id"], t["pdf_page"], t["book_page_ethiopic"], t["chapter_num"], t["chapter_ethiopic"], t["verse_num"], t["verse_ethiopic"], t["geez_title"], t["amharic_title"])
        )

    conn.commit()
    conn.close()

    reader_md_path = os.path.join(out_dir, f"{bkey}_andemta_reader.md")
    with open(reader_md_path, "w", encoding="utf-8") as f:
        f.write(f"# {master_book['title_geez']}\n\n")
        for ch in chapters_list:
            f.write(f"## ምዕራፍ {ch['chapter_ethiopic']} ({ch['chapter_num']}) — {ch.get('geez_incipit', '')}\n\n")
            for v in ch["verses"]:
                if v.get("section_title"):
                    f.write(f"### {v['section_title']}\n\n")
                formatted = v["rejoined_marked_text"].replace("⟪", "**").replace("⟫", "**")
                f.write(f"**[{ch['chapter_ethiopic']}፥{v['verse_ethiopic']}]** *(ገጽ {v['start_book_page_ethiopic']})* {formatted}\n\n")

    diplomatic_md_path = os.path.join(out_dir, f"{bkey}_andemta_diplomatic.md")
    with open(diplomatic_md_path, "w", encoding="utf-8") as f:
        f.write(f"# {master_book['title_geez']} — Diplomatic Line-by-Line Edition\n\n")
        for p in sorted(pages_by_num.keys()):
            p_data = pages_by_num[p]
            f.write(f"## PDF Page {p} — Book Page {p_data.get('book_page_ethiopic') or 'Blank'} ({p_data.get('book_page_arabic') or '-'})\n")
            if p_data.get("running_header"):
                f.write(f"*{p_data['running_header']}*\n\n")
            for col in p_data.get("columns", []):
                f.write(f"### Column {col['column_index']}\n")
                for ln in col.get("lines", []):
                    m = f"[{ln['margin_tag']}] " if ln.get("margin_tag") else ""
                    wrap = "↵" if ln.get("word_wraps_to_next_line") else ""
                    f.write(f"- `L{ln['line_num']:02d}` {m}{ln['text']}{wrap}\n")
                f.write("\n")

    print(f"[{bkey}] Compiled outputs: {json.dumps(master_book['stats'])}", flush=True)

async def process_book(client: genai.Client, book_key: str, workers: int = 8, start_page: int = 1, end_page: Optional[int] = None, force: bool = False):
    cfg = BOOK_CONFIGS[book_key]
    os.makedirs(cfg["pages_dir"], exist_ok=True)
    os.makedirs(cfg["verified_dir"], exist_ok=True)

    max_p = end_page or cfg["total_pages"]
    sem = asyncio.Semaphore(workers)

    print(f"\n==================== [{book_key.upper()}] STAGE 1: EXTRACTING PAGES {start_page}..{max_p} ====================", flush=True)
    tasks = [extract_single_page(client, cfg, p, sem, force=force) for p in range(start_page, max_p + 1)]
    await asyncio.gather(*tasks)

    compile_book_data(cfg)

    print(f"\n==================== [{book_key.upper()}] STAGE 2: YENETA VERIFICATION PAGES {start_page}..{max_p} ====================", flush=True)
    all_pages: Dict[int, Dict] = {}
    for p in range(1, cfg["total_pages"] + 1):
        pp = os.path.join(cfg["pages_dir"], f"page_{p:03d}.json")
        if os.path.exists(pp):
            all_pages[p] = json.load(open(pp, encoding="utf-8"))

    v_tasks = [verify_single_page(client, cfg, p, all_pages, sem, force=force) for p in range(start_page, max_p + 1)]
    await asyncio.gather(*v_tasks)

    compile_book_data(cfg)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--books", type=str, default="markos,lukas,yohannes", help="Comma-separated book keys")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    client = genai.Client()
    book_list = [b.strip() for b in args.books.split(",") if b.strip()]
    for bkey in book_list:
        end_p = args.end if args.end > 0 else None
        await process_book(client, bkey, workers=args.workers, start_page=args.start, end_page=end_p, force=args.force)

if __name__ == "__main__":
    asyncio.run(main())
