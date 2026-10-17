#!/usr/bin/env python3
"""
Unified Two-Stage Extraction, Yeneta Verification, and Compilation Pipeline
for the 9 Dynamic-Spread New Testament Andemta Books:
  5. Acts (`acts` - ግብረ ሐዋርያት, 91 pages, 28 chapters)
  6. 1 Peter (`peter1` - መልእክተ ጴጥሮስ ቀዳማዊ, 31 pages, 5 chapters)
  7. 2 Peter (`peter2` - መልእክተ ጴጥሮስ ካልዕ, 13 pages, 3 chapters)
  8. 1 John (`john1` - መልእክተ ዮሐንስ ቀዳማዊ, 15 pages, 5 chapters)
  9. 2 John (`john2` - መልእክተ ዮሐንስ ካልዕ, 3 pages, 1 chapter)
 10. 3 John (`john3` - መልእክተ ዮሐንስ ሣልስ, 3 pages, 1 chapter)
 11. James (`james` - መልእክተ ያዕቆብ, 14 pages, 5 chapters)
 12. Jude (`judah` - መልእክተ ይሁዳ, 4 pages, 1 chapter)
 13. Revelation (`revelation` - ራእየ ዮሐንስ, 71 pages, 22 chapters)
"""

import argparse
import asyncio
import glob
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import pymupdf
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel, Field

load_dotenv()

BOOKS_CONFIG: Dict[str, Dict] = {
    "acts": {
        "key": "acts",
        "pdf_path": "/Users/senaymacstudio1/Downloads/Acts.pdf",
        "data_dir": "data/acts",
        "raw_images_dir": "data/acts/raw_images",
        "columns_dir": "data/acts/columns",
        "out_dir": "data/acts/extracted",
        "pages_dir": "data/acts/extracted/pages",
        "verified_dir": "data/acts/extracted/verified",
        "title_geez": "ግብረ ሐዋርያት አንድምታ ትርጓሜ",
        "title_english": "Acts of the Apostles Andemta Commentary (ግብረ ሐዋርያት)",
        "short_geez": "ግብረ ሐዋርያት",
        "total_pages": 91,
        "max_chapters": 28,
    },
    "peter1": {
        "key": "peter1",
        "pdf_path": "/Users/senaymacstudio1/Downloads/Peter 1st epistle.pdf",
        "data_dir": "data/peter1",
        "raw_images_dir": "data/peter1/raw_images",
        "columns_dir": "data/peter1/columns",
        "out_dir": "data/peter1/extracted",
        "pages_dir": "data/peter1/extracted/pages",
        "verified_dir": "data/peter1/extracted/verified",
        "title_geez": "መልእክተ ጴጥሮስ ቀዳማዊ አንድምታ ትርጓሜ",
        "title_english": "First Epistle of St. Peter Andemta Commentary (፩ኛ ጴጥሮስ)",
        "short_geez": "፩ኛ ጴጥሮስ",
        "total_pages": 31,
        "max_chapters": 5,
    },
    "peter2": {
        "key": "peter2",
        "pdf_path": "/Users/senaymacstudio1/Downloads/Peter 2nd epistle.pdf",
        "data_dir": "data/peter2",
        "raw_images_dir": "data/peter2/raw_images",
        "columns_dir": "data/peter2/columns",
        "out_dir": "data/peter2/extracted",
        "pages_dir": "data/peter2/extracted/pages",
        "verified_dir": "data/peter2/extracted/verified",
        "title_geez": "መልእክተ ጴጥሮስ ካልዕ አንድምታ ትርጓሜ",
        "title_english": "Second Epistle of St. Peter Andemta Commentary (፪ኛ ጴጥሮስ)",
        "short_geez": "፪ኛ ጴጥሮስ",
        "total_pages": 13,
        "max_chapters": 3,
    },
    "john1": {
        "key": "john1",
        "pdf_path": "/Users/senaymacstudio1/Downloads/John 1st epistle.pdf",
        "data_dir": "data/john1",
        "raw_images_dir": "data/john1/raw_images",
        "columns_dir": "data/john1/columns",
        "out_dir": "data/john1/extracted",
        "pages_dir": "data/john1/extracted/pages",
        "verified_dir": "data/john1/extracted/verified",
        "title_geez": "መልእክተ ዮሐንስ ቀዳማዊ አንድምታ ትርጓሜ",
        "title_english": "First Epistle of St. John Andemta Commentary (፩ኛ ዮሐንስ)",
        "short_geez": "፩ኛ ዮሐንስ",
        "total_pages": 15,
        "max_chapters": 5,
    },
    "john2": {
        "key": "john2",
        "pdf_path": "/Users/senaymacstudio1/Downloads/john 2nd epistle.pdf",
        "data_dir": "data/john2",
        "raw_images_dir": "data/john2/raw_images",
        "columns_dir": "data/john2/columns",
        "out_dir": "data/john2/extracted",
        "pages_dir": "data/john2/extracted/pages",
        "verified_dir": "data/john2/extracted/verified",
        "title_geez": "መልእክተ ዮሐንስ ካልዕ አንድምታ ትርጓሜ",
        "title_english": "Second Epistle of St. John Andemta Commentary (፪ኛ ዮሐንስ)",
        "short_geez": "፪ኛ ዮሐንስ",
        "total_pages": 3,
        "max_chapters": 1,
    },
    "john3": {
        "key": "john3",
        "pdf_path": "/Users/senaymacstudio1/Downloads/john 3rd epistle.pdf",
        "data_dir": "data/john3",
        "raw_images_dir": "data/john3/raw_images",
        "columns_dir": "data/john3/columns",
        "out_dir": "data/john3/extracted",
        "pages_dir": "data/john3/extracted/pages",
        "verified_dir": "data/john3/extracted/verified",
        "title_geez": "መልእክተ ዮሐንስ ሣልስ አንድምታ ትርጓሜ",
        "title_english": "Third Epistle of St. John Andemta Commentary (፫ኛ ዮሐንስ)",
        "short_geez": "፫ኛ ዮሐንስ",
        "total_pages": 3,
        "max_chapters": 1,
    },
    "james": {
        "key": "james",
        "pdf_path": "/Users/senaymacstudio1/Downloads/james.pdf",
        "data_dir": "data/james",
        "raw_images_dir": "data/james/raw_images",
        "columns_dir": "data/james/columns",
        "out_dir": "data/james/extracted",
        "pages_dir": "data/james/extracted/pages",
        "verified_dir": "data/james/extracted/verified",
        "title_geez": "መልእክተ ያዕቆብ አንድምታ ትርጓሜ",
        "title_english": "Epistle of St. James Andemta Commentary (መልእክተ ያዕቆብ)",
        "short_geez": "መልእክተ ያዕቆብ",
        "total_pages": 14,
        "max_chapters": 5,
    },
    "judah": {
        "key": "judah",
        "pdf_path": "/Users/senaymacstudio1/Downloads/judah.pdf",
        "data_dir": "data/judah",
        "raw_images_dir": "data/judah/raw_images",
        "columns_dir": "data/judah/columns",
        "out_dir": "data/judah/extracted",
        "pages_dir": "data/judah/extracted/pages",
        "verified_dir": "data/judah/extracted/verified",
        "title_geez": "መልእክተ ይሁዳ አንድምታ ትርጓሜ",
        "title_english": "Epistle of St. Jude Andemta Commentary (መልእክተ ይሁዳ)",
        "short_geez": "መልእክተ ይሁዳ",
        "total_pages": 4,
        "max_chapters": 1,
    },
    "revelation": {
        "key": "revelation",
        "pdf_path": "/Users/senaymacstudio1/Downloads/revelation.pdf",
        "data_dir": "data/revelation",
        "raw_images_dir": "data/revelation/raw_images",
        "columns_dir": "data/revelation/columns",
        "out_dir": "data/revelation/extracted",
        "pages_dir": "data/revelation/extracted/pages",
        "verified_dir": "data/revelation/extracted/verified",
        "title_geez": "ራእየ ዮሐንስ አንድምታ ትርጓሜ",
        "title_english": "Revelation of St. John Andemta Commentary (ራእየ ዮሐንስ)",
        "short_geez": "ራእየ ዮሐንስ",
        "total_pages": 71,
        "max_chapters": 22,
    },
}

# --- Ethiopic Numerals ---
ETH_ONES = ["", "፩", "፪", "፫", "፬", "፭", "፮", "፯", "፰", "፱"]
ETH_TENS = ["", "፲", "፳", "፴", "፵", "፶", "፷", "፸", "፹", "፺"]
ETH_VALS = {
    "፩": 1, "፪": 2, "፫": 3, "፬": 4, "፭": 5, "፮": 6, "፯": 7, "፰": 8, "፱": 9,
    "፲": 10, "፳": 20, "፴": 30, "፵": 40, "፶": 50, "፷": 60, "፸": 70, "፹": 80, "፺": 90,
    "፻": 100,
}


def int_to_ethiopic(n: Optional[int]) -> str:
    if not n or n <= 0:
        return ""
    if n < 100:
        return ETH_TENS[n // 10] + ETH_ONES[n % 10]
    hundreds = n // 100
    rem = n % 100
    prefix = "" if hundreds == 1 else int_to_ethiopic(hundreds)
    return prefix + "፻" + int_to_ethiopic(rem)


def ethiopic_to_int(s: str) -> Optional[int]:
    if not s:
        return None
    s = re.sub(r"[^\u1369-\u137C]", "", s.strip())
    if not s:
        return None
    if "፻" in s:
        parts = s.split("፻", 1)
        h_part = parts[0]
        r_part = parts[1]
        h_val = 1 if not h_part else sum(ETH_VALS.get(ch, 0) for ch in h_part)
        r_val = sum(ETH_VALS.get(ch, 0) for ch in r_part)
        return h_val * 100 + r_val
    val = sum(ETH_VALS.get(ch, 0) for ch in s)
    return val if val > 0 else None


# --- Pydantic Schemas (Identical to process_gospel_books.py) ---

class UncertainSpan(BaseModel):
    printed_text: str = Field(description="Exact characters printed or visible")
    alternative: str = Field(description="Suggested reading or clarification")
    note: str = Field(description="Brief philological or visual explanation")


class DiplomaticLine(BaseModel):
    line_num: int = Field(description="1-based line number from top to bottom of this column")
    margin_tag: Optional[str] = Field(
        default=None,
        description="Ethiopic verse numeral at the start of a verse or in the left margin (e.g. '፩', '፪', '፲፭'), or null if none"
    )
    line_type: str = Field(
        description="One of: 'chapter_title', 'section_title', 'body', 'colophon'"
    )
    text: str = Field(
        description="Exact character-for-character diplomatic transcription of the line. Wrap root Ge'ez scripture words/phrases (printed in smaller/finer font) in ⟪ and ⟫. Never include ↵."
    )
    word_wraps_to_next_line: bool = Field(
        description="True if the last word on this line is hyphenated/split across the line break onto the next line"
    )
    uncertain: List[UncertainSpan] = Field(default_factory=list)


class ColumnTranscription(BaseModel):
    column_index: int = Field(description="1-based column index from left to right (1..N)")
    lines: List[DiplomaticLine]


class DynamicPageTranscription(BaseModel):
    book_page_ethiopic: str = Field(
        description="Ethiopic page number(s) printed at the top outer corners of the spread/page (e.g., '፩', '፪ | ፫', '፻፴፯ | ፻፴፰')"
    )
    running_header: str = Field(
        description="Running header text at top of the page(s) (e.g., 'ግብረ ፡ ሐዋርያት ።' or 'ሰብዐቱ ፡ መልእክታተ ፡ ሐዋርያ ።' or 'ራእየ ፡ ዮሐንስ ።')"
    )
    columns: List[ColumnTranscription] = Field(
        description="Columns in exact left-to-right order (1..N)"
    )


class LineCorrection(BaseModel):
    column_index: int = Field(description="1-based column index (1..N)")
    line_num: int = Field(description="1-based line_num from the existing transcription")
    old_text: str = Field(description="The previous Stage-1 text of this line")
    corrected_text: str = Field(
        description="The corrected text of this line (preserving ⟪ and ⟫ markers around root Ge'ez scripture words; NEVER include ↵)"
    )
    word_wraps_to_next_line: bool = Field(
        description="True if the last word on this line splits mid-word onto the next line"
    )
    visual_confusable_pair: str = Field(
        description="The exact visually confused characters fixed, e.g. 'ሺ -> ቢ', 'ዘርአ -> ዘርእ', 'ሖ -> ሐ'"
    )
    reason: str = Field(
        description="Brief philological + visual explanation of why the ink-bleed/faded glyph was misread and how the image + Ge'ez/Amharic grammar confirms the correction"
    )


class PageVerificationResult(BaseModel):
    corrections: List[LineCorrection] = Field(
        default_factory=list,
        description="List of lines that had OCR lookalike/ink-bleed errors and their verified corrections. Empty if all lines are 100% accurate."
    )
    remaining_uncertain: List[UncertainSpan] = Field(
        default_factory=list,
        description="Only genuine print/typesetting anomalies in the original physical book where the printed metal type itself has a typo."
    )


# --- Dynamic Column Detection & Image Enhancement ---

def enhance_crop(crop_bgr: np.ndarray) -> np.ndarray:
    """2x Lanczos upscale + CLAHE contrast enhancement + subtle unsharp mask."""
    h, w = crop_bgr.shape[:2]
    up = cv2.resize(crop_bgr, (w * 2, h * 2), interpolation=cv2.INTER_LANCZOS4)
    lab = cv2.cvtColor(up, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_eq = clahe.apply(l)
    lab_eq = cv2.merge((l_eq, a, b))
    enhanced = cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)
    blur = cv2.GaussianBlur(enhanced, (0, 0), 1.2)
    sharp = cv2.addWeighted(enhanced, 1.4, blur, -0.4, 0)
    return sharp


def find_valley(prof: np.ndarray, x0: int, x1: int) -> Tuple[int, float]:
    kernel = np.ones(9) / 9.0
    seg = prof[x0:x1]
    if len(seg) == 0:
        return (x0 + x1) // 2, 0.0
    sm = np.convolve(seg, kernel, mode="same")
    idx = int(np.argmin(sm))
    return x0 + idx, float(sm[idx])


def get_dynamic_column_ranges(book_key: str, page_num: int, im_gray: np.ndarray) -> List[Tuple[int, int]]:
    """
    Returns a list of (x_start, x_end) pixel ranges for each column on `page_num`
    of `book_key`, tailored to all 7 layout types across the 245 pages.
    """
    h, w = im_gray.shape
    pad = max(28, int(w * 0.018))
    prof = (im_gray[int(h * 0.16):int(h * 0.85), :] < 180).astype(np.float32).mean(axis=0)

    # 1. Single-column pages
    if book_key == "peter1" and page_num == 1:
        return [(int(w * 0.27), int(w * 0.78))]
    if book_key == "revelation" and page_num == 71:
        return [(int(w * 0.48), int(w * 0.98))]

    # 2. Single centered book pages with 2 columns
    if (
        (book_key == "acts" and page_num == 1)
        or (book_key == "peter2" and page_num == 1)
        or (book_key == "john1" and page_num in (1, 15))
        or (book_key == "john2" and page_num == 3)
        or (book_key == "john3" and page_num == 3)
    ):
        xc, vc = find_valley(prof, int(w * 0.43), int(w * 0.57))
        if vc > 0.04:
            xc = int(w * 0.50)
        return [
            (int(w * 0.22), min(w, xc + pad)),
            (max(0, xc - pad), int(w * 0.79)),
        ]

    # 3. Single right-shifted book page with 2 columns (judah page 4)
    if book_key == "judah" and page_num == 4:
        xc, vc = find_valley(prof, int(w * 0.50), int(w * 0.63))
        if vc > 0.04:
            xc = int(w * 0.565)
        return [
            (int(w * 0.31), min(w, xc + pad)),
            (max(0, xc - pad), int(w * 0.82)),
        ]

    # 4. Spread where left half is blank and right half has 2 columns (revelation page 4)
    if book_key == "revelation" and page_num == 4:
        xr, vr = find_valley(prof, int(w * 0.66), int(w * 0.80))
        if vr > 0.04:
            xr = int(w * 0.73)
        return [
            (int(w * 0.48), min(w, xr + pad)),
            (max(0, xr - pad), int(w * 0.98)),
        ]

    # 5. Two-wide-column spreads (Left Half = 1 wide col, Right Half = 1 wide col)
    if (
        (book_key == "peter1" and page_num in (2, 3, 4, 5))
        or (book_key == "revelation" and page_num in (1, 2, 3, 70))
    ):
        return [
            (int(w * 0.01), int(w * 0.51)),
            (int(w * 0.48), int(w * 0.99)),
        ]

    # 6. Three-column mixed spreads
    if book_key == "peter1" and page_num == 6:
        xr, vr = find_valley(prof, int(w * 0.68), int(w * 0.82))
        if vr > 0.04:
            xr = int(w * 0.75)
        return [
            (int(w * 0.01), int(w * 0.50)),
            (int(w * 0.48), min(w, xr + pad)),
            (max(0, xr - pad), int(w * 0.99)),
        ]

    if (book_key == "revelation" and page_num == 69) or (book_key == "acts" and page_num == 91):
        xl, vl = find_valley(prof, int(w * 0.19), int(w * 0.32))
        if vl > 0.04:
            xl = int(w * 0.258)
        return [
            (int(w * 0.01), min(w, xl + pad)),
            (max(0, xl - pad), int(w * 0.50)),
            (int(w * 0.48), int(w * 0.99)),
        ]

    # 7. Standard 4-column Two-Page Spread (Left Col 1, Left Col 2, Right Col 1, Right Col 2)
    xl, vl = find_valley(prof, int(w * 0.19), int(w * 0.32))
    if vl > 0.04:
        prof_top = (im_gray[int(h * 0.14):int(h * 0.28), :] < 180).astype(np.float32).mean(axis=0)
        prof_bot = (im_gray[int(h * 0.78):int(h * 0.90), :] < 180).astype(np.float32).mean(axis=0)
        xl_t, vl_t = find_valley(prof_top, int(w * 0.19), int(w * 0.32))
        xl_b, vl_b = find_valley(prof_bot, int(w * 0.19), int(w * 0.32))
        if min(vl_t, vl_b) <= 0.04:
            xl = xl_t if vl_t <= vl_b else xl_b
        else:
            xl = int(w * 0.256)

    xr, vr = find_valley(prof, int(w * 0.67), int(w * 0.81))
    if vr > 0.04:
        prof_top = (im_gray[int(h * 0.14):int(h * 0.28), :] < 180).astype(np.float32).mean(axis=0)
        prof_bot = (im_gray[int(h * 0.78):int(h * 0.90), :] < 180).astype(np.float32).mean(axis=0)
        xr_t, vr_t = find_valley(prof_top, int(w * 0.67), int(w * 0.81))
        xr_b, vr_b = find_valley(prof_bot, int(w * 0.67), int(w * 0.81))
        if min(vr_t, vr_b) <= 0.04:
            xr = xr_t if vr_t <= vr_b else xr_b
        else:
            xr = int(w * 0.736)

    return [
        (int(w * 0.01), min(w, xl + pad)),
        (max(0, xl - pad), int(w * 0.50)),
        (int(w * 0.48), min(w, xr + pad)),
        (max(0, xr - pad), int(w * 0.99)),
    ]


def prepare_dynamic_crops(cfg: Dict, pdf_page: int) -> Tuple[Image.Image, List[Image.Image], List[List[int]]]:
    """Loads upright raw page image, slices dynamic column crops, saves them to columns_dir, and returns PIL images."""
    raw_dir = Path(cfg["raw_images_dir"])
    col_root = Path(cfg["columns_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    col_root.mkdir(parents=True, exist_ok=True)

    raw_path = raw_dir / f"page_{pdf_page:03d}.jpg"
    if not raw_path.exists():
        doc = pymupdf.open(cfg["pdf_path"])
        page = doc[pdf_page - 1]
        rot = page.rotation
        imgs = page.get_images(full=True)
        xref = imgs[0][0]
        base_img = doc.extract_image(xref)
        arr = np.frombuffer(base_img["image"], np.uint8)
        im = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if rot == 90:
            im = cv2.rotate(im, cv2.ROTATE_90_CLOCKWISE)
        elif rot == 270:
            im = cv2.rotate(im, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif rot == 180:
            im = cv2.rotate(im, cv2.ROTATE_180)
        cv2.imwrite(str(raw_path), im, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        doc.close()

    img_bgr = cv2.imread(str(raw_path))
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = img_gray.shape
    col_ranges = get_dynamic_column_ranges(cfg["key"], pdf_page, img_gray)

    page_col_dir = col_root / f"page_{pdf_page:03d}"
    page_col_dir.mkdir(parents=True, exist_ok=True)

    boxes = []
    crops_pil = []
    for c_idx, (x0, x1) in enumerate(col_ranges, start=1):
        boxes.append([x0, 0, x1, h])
        col_file = page_col_dir / f"col_{c_idx}.jpg"
        if not col_file.exists():
            sub = img_bgr[:, x0:x1]
            enh = enhance_crop(sub)
            cv2.imwrite(str(col_file), enh, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        else:
            enh = cv2.imread(str(col_file))
        crops_pil.append(Image.fromarray(cv2.cvtColor(enh, cv2.COLOR_BGR2RGB)))

    full_pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    return full_pil, crops_pil, boxes


# --- Prompts for Stage 1 & Stage 2 ---

def build_stage1_prompt(cfg: Dict, pdf_page: int, num_cols: int) -> str:
    col_desc = "\n".join(
        f"{i+1}. Column {i} (2x zoom crop in left-to-right reading order)"
        for i in range(1, num_cols + 1)
    )
    return f"""You are the world's foremost Ethiopian Orthodox Yeneta (ሊቀ ሊቃውንት) and philologist in Classical Ethiopic (Ge'ez / ልሳነ ግዕዝ) and Amharic Andemta Commentary ({cfg['title_geez']} — {cfg['title_english']}).
Transcribe PDF Page {pdf_page} with 100% character-level fidelity into exactly {num_cols} column(s) (`column_index` 1 through {num_cols}).

Images provided:
1. Full upright scan image
{col_desc}

STRICT PHILOLOGICAL & VISUAL RULES:
1. Transcribe EVERY physical line of each column (`column_index` = 1..{num_cols}) in exact top-to-bottom order. Never skip, summarize, or merge lines.
2. Preserve exact Ethiopic Fidels (ሀ/ሐ/ኀ, ሰ/ሠ, አ/ዐ, ጸ/ፀ, ቍ/ቁ, ኵ/ኩ) and exact punctuation (፡, ።, ፤, ፥). Do NOT modernize archaic Andemta forms (keep ሁነው, ለኒህ, ደንጊያ, ኖሎት, አባግዕ, ፩ዱ, etc. exactly as printed).
3. GUARD AGAINST LEAD-TYPE INK BLEED LOOKALIKES:
   - Watch out for top-serif ink bleed making `ቢ` look like `ሺ` or `ቨ` (e.g. `ቢያነሱላቸው`, `ቢሉ`), or `በ` vs `ባ`, `ሂ` vs `ሄ`, `ሐ` vs `ሖ`, `አ` vs `እ`, `ን` vs `ሩ`, `ግ` vs `ም`, `፷` vs `፰`.
   - Always mentally rejoin words split across lines (`word_wraps_to_next_line = true`) to verify that both Classical Ge'ez (`ልሳነ ግዕዝ`) morphology and Amharic (`አማርኛ`) words are 100% real, grammatical words matching {cfg['short_geez']}.
   - Output ONLY pure Ethiopic Fidels, punctuation, and `⟪...⟫` markers (never output non-Ethiopic characters or `↵`).
4. GE'EZ ROOT SCRIPTURE (`⟪...⟫`) & VERSE NUMBERS (`margin_tag`):
   - In this edition, the root Ge'ez scripture verses and sub-clauses of {cfg['short_geez']} are printed in a SMALLER, FINER font, often starting with an Ethiopic verse numeral (`፩ ፤ ...`, `፪ ፤ ...`, `፲፭ ፤ ...`).
   - Wrap ALL root Ge'ez scripture words/clauses of {cfg['short_geez']} in `⟪...⟫`.
   - Record the Ethiopic verse numeral opening each verse (`"፩"`, `"፪"`, `"፫"`, `"፲፭"`, etc.) in `margin_tag`! Do NOT put `margin_tag` on inline biblical cross-references inside the commentary (like `ሉቃ ፡ ፳፬ ፥ ፵፱ ።` or `በል ፡ ቍ ፡ ፫ ።`).
5. Set `line_type` to:
   - `"chapter_title"` ONLY for major chapter headings containing `ምዕራፍ` (e.g., `ምዕራፍ ፡ ፩ ።`, `ምዕራፍ ፡ ፪ ፤ ክፍል ፡ ፫ ።`). Note: in Acts, liturgical division markers inside a verse like `፬ ፤ ክፍል ፡ ፩ ፤ ...` have `margin_tag = "፬"` and `line_type = "body"`.
   - `"section_title"` for pericope/prologue subheadings (e.g., `መቅድም ።`, `ንባብ ።`, `ትርጓሜ ።`, `ማረሚያ ።`)
   - `"colophon"` for concluding colophon lines at the end of the book
   - `"body"` for all standard verse, prologue, and commentary lines
6. Set `word_wraps_to_next_line = true` whenever the last word of a line splits mid-word onto the next line.
"""


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


VERIFY_PROMPT = """You are the world's foremost Ethiopian Orthodox Yeneta (ሊቀ ሊቃውንት) and Philologist of Classical Ge'ez (ልሳነ ግዕዝ) and Amharic Andemta Commentary ({title_geez} — {title_english}).

We are performing Stage-2 Philological & Visual Verification on PDF Page {pdf_page} (Book Page {book_page_eth}).
In Stage 1, an OCR pass transcribed each line in isolation. Because this old lead-type printing has ink bleed, uneven serif pressure, and mid-word line wraps (`↵`), Stage 1 occasionally misread visually confusable Fidels.

YOUR TASK:
Inspect the provided 2x zoomed column images AND read the Rejoined Word Stream carefully word-by-word in both **Classical Ge'ez (ልሳነ ግዕዝ)** and **Amharic (አማርኛ)**.
Find and fix EVERY single word where Stage 1 misread a visually similar Fidel or numeral.

CRITICAL RULES FOR GE'EZ (ልሳነ ግዕዝ) VERIFICATION:
1. **Root Scripture Quotes (`⟪...⟫`) & Patristic Citations (`እንዲል`)**:
   - Verify every Ge'ez word against canonical Ge'ez New Testament ({short_geez}) phrasing and Classical Ge'ez morphology (construct states `-አ`/`-ተ`, pronominal suffixes `-ሁ`/`-ሆሙ`/`-ክሙ`/`-ከ`, subjunctive/gerundive endings, accusative markers, prepositions `ውስተ`, `እምኀበ`, `በእንተ`).
   - Watch for ink-bleed confusables in Ge'ez:
     - 1st order (`ግዕዝ`) vs 4th order (`ራብዕ`) vs 6th order (`ሳድስ`): e.g. `ዘርእከ` vs `ዘርአከ`, `ለእግዚእነ` vs `ለአግዚአነ`, `ሐዊረክሙ` vs `ሖዊረክሙ`.
     - Visually similar base characters: `ሀ/ሐ/ኀ`, `ሰ/ሠ`, `አ/ዐ`, `ጸ/ፀ`, `በ/ለ/ሊ`, `ተ/ቶ/ት`, `ነ/ኒ/ና`, `ወ/ዐ`, `ደ/ድ/ዳ`, `ገ/ግ/ጎ`, `ፈ/ፍ/ፎ`, `ይ/ደ`.
     - Ethiopic numerals: `፷` (60) vs `፰` (8), `፸` (70) vs `፯` (7), `፳` (20) vs `፺` (90), `፴` (30) vs `፫` (3).

CRITICAL RULES FOR AMHARIC (አማርኛ) ANDEMTA VERIFICATION:
2. **Continuous Word Sense Across Line Wraps (`↵`)**:
   - Join split words across `↵` and across column boundaries and verify the complete word makes 100% grammatical and theological sense in the Andemta commentary.
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
    txt = txt.replace("נ", "ን").replace("ئ", "እ")
    return txt


# --- Stage 1 Extraction & Stage 2 Verification Workers ---

async def extract_single_page(
    client: genai.Client,
    cfg: Dict,
    pdf_page: int,
    sem: asyncio.Semaphore,
    force: bool = False,
):
    out_path = os.path.join(cfg["pages_dir"], f"page_{pdf_page:03d}.json")
    if os.path.exists(out_path) and not force:
        return {"pdf_page": pdf_page, "status": "cached"}

    async with sem:
        for attempt in range(20):
            try:
                t0 = time.time()
                full_pil, crops, boxes = prepare_dynamic_crops(cfg, pdf_page)
                num_cols = len(crops)
                prompt = build_stage1_prompt(cfg, pdf_page, num_cols)
                contents = [full_pil] + crops + [prompt]

                resp = await client.aio.models.generate_content(
                    model="gemini-4-argon",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=DynamicPageTranscription,
                        temperature=0.0,
                    ),
                )
                parsed = json.loads(resp.text)
                for col in parsed.get("columns", []):
                    for ln in col.get("lines", []):
                        ln["text"] = clean_ethiopic_text(ln.get("text", ""))

                book_eth = parsed.get("book_page_ethiopic", "")
                first_eth = book_eth.split("|")[0].strip() if book_eth else ""
                book_num = ethiopic_to_int(first_eth) or pdf_page

                payload = {
                    "pdf_page": pdf_page,
                    "book_page_arabic": book_num,
                    "book_page_ethiopic": book_eth or int_to_ethiopic(pdf_page),
                    "page_type": f"commentary_{num_cols}col",
                    "running_header": parsed.get("running_header", ""),
                    "column_boxes": boxes,
                    "columns": parsed.get("columns", []),
                }

                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)

                dt = time.time() - t0
                n_lines = sum(len(c.get("lines", [])) for c in payload.get("columns", []))
                print(
                    f"[{cfg['key']}] Stage-1 Page {pdf_page:3d}/{cfg['total_pages']} (Book {payload['book_page_ethiopic']}): "
                    f"{num_cols} cols, {n_lines} lines in {dt:.1f}s",
                    flush=True,
                )
                return payload
            except Exception as e:
                err_s = str(e)
                wait_s = (15.0 + 5.0 * attempt) if ("429" in err_s or "RESOURCE_EXHAUSTED" in err_s) else (3.0 * (attempt + 1))
                print(f"[{cfg['key']}] Stage-1 Page {pdf_page:3d} attempt {attempt+1} error (sleeping {wait_s:.0f}s): {e}", flush=True)
                await asyncio.sleep(wait_s)

        raise RuntimeError(f"[{cfg['key']}] Failed Stage-1 extraction on page {pdf_page}")


async def verify_single_page(
    client: genai.Client,
    cfg: Dict,
    pdf_page: int,
    all_pages: Dict[int, Dict],
    sem: asyncio.Semaphore,
    force: bool = False,
):
    verify_log_path = os.path.join(cfg["verified_dir"], f"verify_{pdf_page:03d}.json")
    page_path = os.path.join(cfg["pages_dir"], f"page_{pdf_page:03d}.json")

    if not os.path.exists(page_path):
        return {"pdf_page": pdf_page, "status": "missing"}

    p_data = all_pages[pdf_page]
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
                full_pil, crops, _ = prepare_dynamic_crops(cfg, pdf_page)
                prompt = VERIFY_PROMPT.format(
                    pdf_page=pdf_page,
                    book_page_eth=book_eth,
                    title_geez=cfg["title_geez"],
                    title_english=cfg["title_english"],
                    short_geez=cfg["short_geez"],
                    preview_text=preview_text,
                )
                contents = [full_pil] + crops + [prompt]

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

                print(
                    f"[{cfg['key']}] Stage-2 Verified Page {pdf_page:3d}/{cfg['total_pages']} ({book_eth}): "
                    f"{applied} lines corrected in {dt:.1f}s",
                    flush=True,
                )
                return {"pdf_page": pdf_page, "status": "verified", "corrections": applied}
            except Exception as e:
                err_s = str(e)
                wait_s = (15.0 + 5.0 * attempt) if ("429" in err_s or "RESOURCE_EXHAUSTED" in err_s) else (3.0 * (attempt + 1))
                print(f"[{cfg['key']}] Stage-2 Page {pdf_page:3d} attempt {attempt+1} error (sleeping {wait_s:.0f}s): {e}", flush=True)
                await asyncio.sleep(wait_s)

        raise RuntimeError(f"[{cfg['key']}] Failed Stage-2 verification on page {pdf_page}")


# --- Compilation (Identical Schema to process_gospel_books.py) ---

CHAPTER_RE = re.compile(r"ምዕራፍ?[\s፡፥፤።]*([፩-፼ወ]+)")
CROSS_REF_START_RE = re.compile(
    r"^⟪?[፩-፼]+\s*[፡፥]\s*(?:[፩-፼]+|ቆሮ|ጴጥ|ጢሞ|ተሰ|ዮሐ|ነገሥ|ሳሙ|ዜና|መቃ|ዕዝ|ሮሜ|ማቴ|ማር|ሉቃ|ዘፀአ|ዘፍ|ዘሌ|ዘኍ|ዘዳ|ኢሳ|ኤር|ሕዝ|ዳን|መዝ|ምሳ|ዕብ|ያዕ|ይሁዳ|ራእ|ም\b)"
)
REAL_INLINE_VERSE_RE = re.compile(r"^⟪?([፩-፼]+)\s*፤|^⟪([፩-፼]+)\s*[፤፥፡]")
TRUE_VERSE_MARKER_RE = re.compile(
    r"^(?:⟪\s*)?([፩-፼]+)\s*፤(?:\s*ክፍል\s*[:፡፥፤]?\s*[፩-፼]+\s*[።፤፥፡]?)?\s*⟪?"
    r"|^⟪\s*([፩-፼]+)\s*[፤፥፡]\s*(?=[ሀ-ፖ])"
)
MIDLINE_VERSE_SPLIT_RE = re.compile(
    r"^(.+?።\s*)((?:⟪\s*)?[፩-፼]+\s*፤\s*(?:ክፍል\s*[:፡፥፤]?\s*[፩-፼]+\s*[።፤፥፡]?\s*)?⟪.*)$"
)


def is_chapter_header_line(ln: Dict) -> Optional[int]:
    lt = ln.get("line_type", "body")
    clean = ln.get("text", "").replace("⟪", "").replace("⟫", "").replace("↵", "").strip()
    m = CHAPTER_RE.search(clean)
    if (lt == "chapter_title" or (m and len(clean) <= 32)) and m:
        return ethiopic_to_int(m.group(1))
    return None


def is_v1_start_line(ln: Dict) -> bool:
    txt = ln.get("text", "").replace("↵", "").strip()
    clean = txt.replace("⟪", "").replace("⟫", "").strip()
    if CROSS_REF_START_RE.match(txt) or CROSS_REF_START_RE.match(clean):
        return False
    m = REAL_INLINE_VERSE_RE.match(txt)
    if m:
        num_s = m.group(1) or m.group(2)
        if ethiopic_to_int(num_s) == 1:
            return True
    if ln.get("margin_tag") and ethiopic_to_int(ln["margin_tag"].strip()) == 1:
        if ("፤" in clean or "⟪" in txt) and "በል" not in clean:
            return True
    if txt.startswith("፤ ⟪ወከማሁ"):
        return True
    return False


def extract_true_verse_num(txt: str, m_tag: Optional[str]) -> Optional[int]:
    txt_s = txt.strip()
    m = TRUE_VERSE_MARKER_RE.match(txt_s)
    if m:
        num_s = m.group(1) or m.group(2)
        return ethiopic_to_int(num_s)
    if txt_s.startswith("፤ ⟪ወከማሁ"):
        return 1
    if txt_s.startswith("፤ ⟪እንዘ ፡ ከመ ፡ አባግዕ"):
        return 25
    if m_tag and txt_s.startswith("⟪"):
        clean_in = txt_s.replace("⟪", "").strip()
        if not re.match(r"^[፩-፼]+\s*[፡፥]\s*[፩-፼]+", clean_in):
            return ethiopic_to_int(m_tag.strip())
    return None


def order_page_lines(book_key: str, p: int, columns: List[Dict]) -> List[Tuple[int, Dict]]:
    """
    Orders lines across a page, handling 2-column horizontal chapter dividers on (1, 2) or (3, 4) pairs.
    """
    if book_key == "judah" and p == 1:
        out = []
        for col in columns:
            c_idx = col.get("column_index", 1)
            for ln in col.get("lines", []):
                out.append((c_idx, ln))
        return out

    col_map = {col.get("column_index", i + 1): col.get("lines", []) for i, col in enumerate(columns)}
    col_indices = sorted(col_map.keys())
    if len(col_indices) == 4:
        pairs = [(1, 2), (3, 4)]
    elif len(col_indices) == 2:
        pairs = [(col_indices[0], col_indices[1])]
    else:
        out = []
        for c_idx in col_indices:
            for ln in col_map[c_idx]:
                out.append((c_idx, ln))
        return out

    out: List[Tuple[int, Dict]] = []
    for cL, cR in pairs:
        linesL = col_map.get(cL, [])
        linesR = col_map.get(cR, [])

        ch_idx_L = next((i for i, ln in enumerate(linesL) if is_chapter_header_line(ln) is not None), None)
        ch_idx_R = next((i for i, ln in enumerate(linesR) if is_chapter_header_line(ln) is not None), None)

        if ch_idx_L is None and ch_idx_R is None:
            for ln in linesL:
                out.append((cL, ln))
            for ln in linesR:
                out.append((cR, ln))
            continue

        header_ln = linesL[ch_idx_L] if ch_idx_L is not None else linesR[ch_idx_R]
        header_col = cL if ch_idx_L is not None else cR

        if ch_idx_L is not None:
            split_L = ch_idx_L
            if split_L > 0 and linesL[split_L - 1].get("line_type") == "section_title":
                split_L -= 1
            cL_top = linesL[:split_L]
            cL_bottom = [ln for i, ln in enumerate(linesL[split_L:], start=split_L) if i != ch_idx_L]
        else:
            v1_idx_L = next((i for i, ln in enumerate(linesL) if is_v1_start_line(ln)), 0)
            if v1_idx_L > 0 and linesL[v1_idx_L - 1].get("line_type") == "section_title":
                v1_idx_L -= 1
            cL_top = linesL[:v1_idx_L]
            cL_bottom = linesL[v1_idx_L:]

        if ch_idx_R is not None:
            cR_top = linesR[:ch_idx_R]
            cR_bottom = linesR[ch_idx_R + 1:]
        elif len(cL_top) == 0:
            cR_top = []
            cR_bottom = linesR
        else:
            target_idx = min(len(cL_top), len(linesR))
            candidates = []
            for idx_r in range(max(0, target_idx - 4), min(len(linesR), target_idx + 2)):
                t_r = linesR[idx_r].get("text", "").replace("⟪", "").replace("⟫", "").strip()
                if t_r.endswith("።"):
                    candidates.append((abs((idx_r + 1) - len(cL_top)), idx_r + 1))
            if candidates:
                candidates.sort()
                best_split_R = candidates[0][1]
            else:
                best_split_R = target_idx
            cR_top = linesR[:best_split_R]
            cR_bottom = linesR[best_split_R:]

        for ln in cL_top:
            out.append((cL, ln))
        for ln in cR_top:
            out.append((cR, ln))
        out.append((header_col, header_ln))
        for ln in cL_bottom:
            out.append((cL, ln))
        for ln in cR_bottom:
            out.append((cR, ln))

    return out


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
    bkey = cfg["key"]

    chapters_map: Dict[int, Dict] = {}
    all_uncertain: List[Dict] = []
    all_stage2_corrections: List[Dict] = []
    total_lines_count = 0

    curr_ch_num = 1
    curr_ch_eth = "፩"
    seen_ch1_header = False
    curr_v_num = 0
    curr_v_eth = "መቅድም"
    curr_section_title: Optional[str] = f"መቅድም — {cfg['short_geez']}"

    def ensure_chapter(ch_num: int):
        if ch_num not in chapters_map:
            chapters_map[ch_num] = {
                "chapter_num": ch_num,
                "chapter_ethiopic": int_to_ethiopic(ch_num),
                "title_geez": f"ምዕራፍ {int_to_ethiopic(ch_num)} ።",
                "geez_incipit": "",
                "amharic_incipit": "",
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

        ordered_raw = order_page_lines(bkey, p, p_data.get("columns", []))
        expanded_lines = []
        for c_idx, ln in ordered_raw:
            txt = ln.get("text", "").replace("↵", "").strip()
            m_split = MIDLINE_VERSE_SPLIT_RE.match(txt)
            if m_split and ln.get("line_type", "body") == "body":
                part1 = m_split.group(1).strip()
                part2 = m_split.group(2).strip()
                ln1 = dict(ln)
                ln1["text"] = part1
                ln1["margin_tag"] = None
                ln1["word_wraps_to_next_line"] = False
                ln2 = dict(ln)
                ln2["text"] = part2
                expanded_lines.append((c_idx, ln1))
                expanded_lines.append((c_idx, ln2))
            else:
                expanded_lines.append((c_idx, ln))

        for c_idx, ln in expanded_lines:
            l_num = ln.get("line_num", 1)
            l_type = ln.get("line_type", "body")
            txt = ln.get("text", "").replace("↵", "").strip()
            m_tag = ln.get("margin_tag")
            clean_txt = txt.replace("⟪", "").replace("⟫", "").strip()

            ch_num_found = is_chapter_header_line(ln)
            if ch_num_found and 1 <= ch_num_found <= max_ch:
                seen_ch1_header = True
                curr_ch_num = ch_num_found
                curr_ch_eth = int_to_ethiopic(ch_num_found)
                if bkey == "judah" and p == 1 and ch_num_found == 1:
                    curr_v_num = 0
                    curr_v_eth = "መቅድም"
                else:
                    curr_v_num = 1
                    curr_v_eth = "፩"
                    curr_section_title = None
                ch_obj = ensure_chapter(curr_ch_num)
                ch_obj["title_geez"] = clean_txt
                ch_obj["start_pdf_page"] = p
                ch_obj["start_book_page_ethiopic"] = book_eth
                continue

            parsed_v = extract_true_verse_num(txt, m_tag)

            if (not seen_ch1_header or (bkey == "judah" and curr_v_num == 0)) and parsed_v == 1:
                seen_ch1_header = True
                curr_ch_num = 1
                curr_ch_eth = "፩"
                curr_v_num = 1
                curr_v_eth = "፩"
                curr_section_title = None
                ch_obj = ensure_chapter(1)
                ch_obj["start_pdf_page"] = p
                ch_obj["start_book_page_ethiopic"] = book_eth

            if l_type == "section_title":
                curr_section_title = clean_txt

            if parsed_v and seen_ch1_header and 1 <= parsed_v <= 90:
                if (
                    parsed_v == curr_v_num
                    or parsed_v == curr_v_num + 1
                    or (parsed_v > curr_v_num and parsed_v <= curr_v_num + 6)
                    or (curr_v_num <= 2 and curr_v_num <= parsed_v <= 5)
                ):
                    curr_v_num = parsed_v
                    curr_v_eth = int_to_ethiopic(parsed_v)
                    m_tag = curr_v_eth

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
    chapter_index = []
    topical_index = []
    total_verses_count = 0
    for ch_num in sorted(chapters_map.keys()):
        ch_obj = chapters_map[ch_num]
        v_list = []
        seen_sec_in_ch = set()
        for v_num in sorted(ch_obj["verses_map"].keys()):
            v_obj = ch_obj["verses_map"][v_num]
            rejoined = rejoin_lines_text(v_obj["lines"])
            # Merge adjacent ⟫ ⟪
            rejoined = re.sub(r"⟫(\s*)⟪", r"\1", rejoined)
            geez_lemmas = [m.strip() for m in re.findall(r"⟪([^⟫]+)⟫", rejoined) if m.strip()]
            plain_rejoined = rejoined.replace("⟪", "").replace("⟫", "")
            v_obj["rejoined_marked_text"] = rejoined
            v_obj["rejoined_plain_text"] = plain_rejoined
            v_obj["geez_root_lemmas"] = geez_lemmas
            v_list.append(v_obj)
            total_verses_count += 1

            sec = v_obj.get("section_title")
            if (v_num == 1 or (sec and sec not in seen_sec_in_ch)):
                if sec:
                    seen_sec_in_ch.add(sec)
                g_title = geez_lemmas[0][:80] if geez_lemmas else (sec or ch_obj["title_geez"])
                a_title = re.sub(r"⟪[^⟫]*⟫", "", rejoined).strip()[:90]
                topical_index.append({
                    "topic_id": len(topical_index) + 1,
                    "pdf_page": v_obj["start_pdf_page"],
                    "book_page_ethiopic": v_obj["start_book_page_ethiopic"],
                    "chapter_num": ch_num,
                    "chapter_ethiopic": ch_obj["chapter_ethiopic"],
                    "verse_num": v_num,
                    "verse_ethiopic": v_obj["verse_ethiopic"],
                    "geez_title": g_title,
                    "amharic_title": a_title,
                })

        del ch_obj["verses_map"]
        ch_obj["verses"] = v_list

        # Populate chapter incipit from first verse with Ge'ez root lemmas
        first_v = next((v for v in v_list if v["verse_num"] >= 1 and v["geez_root_lemmas"]), None)
        if not first_v and v_list:
            first_v = v_list[0]
        if first_v:
            if first_v["geez_root_lemmas"]:
                ch_obj["geez_incipit"] = first_v["geez_root_lemmas"][0][:80]
            ch_obj["amharic_incipit"] = first_v["rejoined_plain_text"][:90]

        chapter_index.append({
            "chapter_num": ch_num,
            "chapter_ethiopic": ch_obj["chapter_ethiopic"],
            "geez_incipit": ch_obj["geez_incipit"] or ch_obj["title_geez"],
            "amharic_incipit": ch_obj["amharic_incipit"],
        })
        chapters_list.append(ch_obj)

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
            "total_canon_table_pages": 0,
            "total_stage2_corrections": len(all_stage2_corrections),
            "total_uncertain_apparatus_flags": len(all_uncertain),
        },
        "chapter_index": chapter_index,
        "topical_index": topical_index,
        "canon_tables": [],
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
    """)

    for p, p_data in sorted(pages_by_num.items()):
        cur.execute(
            "INSERT INTO pages VALUES (?, ?, ?, ?, ?, ?)",
            (
                p,
                p_data.get("book_page_arabic"),
                p_data.get("book_page_ethiopic"),
                p_data.get("page_type"),
                p_data.get("running_header"),
                json.dumps(p_data, ensure_ascii=False),
            ),
        )

    for ch in chapters_list:
        cur.execute(
            "INSERT INTO chapters VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                ch["chapter_num"],
                ch["chapter_ethiopic"],
                ch["title_geez"],
                ch["geez_incipit"],
                ch["amharic_incipit"],
                ch["start_pdf_page"],
                ch["start_book_page_ethiopic"],
            ),
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
                    v["chapter_num"],
                    v["chapter_ethiopic"],
                    v["verse_num"],
                    v["verse_ethiopic"],
                    v["section_title"],
                    v["start_pdf_page"],
                    v["start_book_page_ethiopic"],
                    geez_joined,
                    v["rejoined_marked_text"],
                    v["rejoined_plain_text"],
                    json.dumps(v["lines"], ensure_ascii=False),
                ),
            )
            rowid = cur.lastrowid
            cur.execute(
                "INSERT INTO verses_fts(rowid, chapter_ethiopic, verse_ethiopic, geez_root_text, rejoined_plain_text) VALUES (?, ?, ?, ?, ?)",
                (rowid, v["chapter_ethiopic"], v["verse_ethiopic"], geez_joined, v["rejoined_plain_text"]),
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


async def process_book(
    client: genai.Client,
    book_key: str,
    workers: int = 8,
    start_page: int = 1,
    end_page: Optional[int] = None,
    force: bool = False,
):
    cfg = BOOKS_CONFIG[book_key]
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
    parser.add_argument(
        "--books",
        type=str,
        default="john2,john3,judah,peter2,james,john1,peter1,revelation,acts",
        help="Comma-separated book keys",
    )
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--compile-only", action="store_true")
    args = parser.parse_args()

    book_list = [b.strip() for b in args.books.split(",") if b.strip()]
    if args.compile_only:
        for bkey in book_list:
            compile_book_data(BOOKS_CONFIG[bkey])
        return

    client = genai.Client()
    for bkey in book_list:
        end_p = args.end if args.end > 0 else None
        await process_book(client, bkey, workers=args.workers, start_page=args.start, end_page=end_p, force=args.force)


if __name__ == "__main__":
    asyncio.run(main())
