import asyncio
import json
import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional
from extract_all_pages import prepare_3col_crops

load_dotenv()

class LineCorrection(BaseModel):
    column_index: int
    line_num: int
    old_text: str = Field(description="Exact text of this line from Draft Pass 1 (without [margin_tag] or ↵)")
    corrected_text: str = Field(description="Corrected text of this line preserving exact line break boundaries and ⟪...⟫ tags")
    word_wraps_to_next_line: bool = Field(description="True if the word at the end of this line continues mid-word onto the next line")
    visual_confusable_pair: str = Field(description="The visually confusable characters involved, e.g. 'ሺ -> ቢ', 'ሩ -> ራ', 'ዘርአ -> ዘርእ', 'ለ፰ -> ለ፷', 'ምን -> ንጐ'")
    reason: str = Field(description="Concise philological (Ge'ez/Amharic) and visual explanation")

class PageVerificationResult(BaseModel):
    corrections: List[LineCorrection]

VERIFY_PROMPT = """You are a Senior Ethiopian Orthodox Yeneta (የኔታ / መምህር — Master Scholar of Classical Ge'ez [ልሳነ ግዕዝ] and Traditional Wengel Andemta Commentary [ወንጌለ ማቴዎስ አንድምታ ትርጓሜ]).

We ran an initial OCR pass (Draft Pass 1) on PDF Page {pdf_page} (Book Page {book_eth}).
Because this is an old lead-type printed book photographed with a phone camera, ink bleed, smudges, and faint serifs frequently make one Ethiopic Fidel look like another visually similar Fidel.

Your task is to audit EVERY SINGLE LINE of Column 1, Column 2, and Column 3 by comparing the Draft Pass 1 text against:
1. The 2x zoomed column images (Images 2, 3, 4) and full page image (Image 1), AND
2. Strict Classical Ge'ez (ልሳነ ግዕዝ) grammar/morphology, canonical Gospel of Matthew Ge'ez text (ወንጌለ ማቴዎስ), canonical Biblical/Patristic Ge'ez citations, and traditional Amharic Andemta vocabulary.

CRITICAL RULES FOR CORRECTIONS:
1. **Catch All Ink-Bleed & Faint-Stroke Fidel Lookalikes in Both Ge'ez and Amharic**:
   - Top-serif ink bleed turning `ቢ` into `ሺ` (e.g., conditional `ቢያነሱላቸው` misread as non-word `ሺያነሱላቸው`), `በ` into `ሰ`/`ሸ`, `ለ` into `ሰ`, `ከ` into `ነ`.
   - Vowel-order misreads (1st ግዕዝ, 2nd ካዕብ, 3rd ሣልስ, 4th ራብዕ, 5th ኃምስ, 6th ሳድስ, 7th ሳብዕ):
     * e.g., plural `ዕውራን` (4th order `ራ`) misread as singular `ዕውሩን` (2nd order `ሩ`),
     * e.g., Ge'ez nominative `ዘርእ` (6th order `እ` in `እምይስሐቅ ይሰመይ ለከ ዘርእ`) misread as `ዘርአ`,
     * e.g., Ge'ez particle `እንከሰ` (`እንከሰ ግዑዝ ውእቱ ወልድ`) misread as `አንከሰ`,
     * e.g., Ge'ez verb `ወአቆመ` (7th order `ቆ`) misread as `ወአቀመ`,
     * e.g., Ge'ez `ከመ ኢያንጐርጕሩ` misread as `ከመኢያምንርጕሩ`,
     * e.g., Amharic `የማዘን` (`የማዘን ደግነት ነው`) misread as `የሚዘን`.
   - Base-shape lookalikes: `ደ`/`ይ`, `ን`/`ጎ`, `ዐ`/`ዓ`/`ዕ`/`አ`/`እ`, `ኀ`/`ነ`/`ከ`/`ገ`, `ጸ`/`ፀ`/`ዘ`, `ሐ`/`ሕ`/`ሐ`, `ወ`/`መ`, `ረ`/`ፈ`, `ቀ`/`ተ`, `ሥ`/`ሠ`.
   - Ethiopic numeral lookalikes: `፷` (60) misread as `፰` (8) (e.g. `ለ፶ ለ፷` misread as `ለ፶ ለ፰`), `፵` (40) vs `ም`, `፳` (20) vs `፴` (30) vs `፸` (70).
2. **STRICT VISUAL GROUNDING — NO UNRELATED SYNONYM GUESSING**:
   - ONLY correct a character when the printed glyph in the 2x zoomed column image actually supports the corrected Fidel (i.e. it is a visual lookalike / ink-bleed / vowel-order / spacing error, or a genuine misread of the image).
   - NEVER replace a clearly printed word (such as `አለ`) with a visually unrelated word (such as `ተወ`) if the printed letters in the image are clearly `አለ`!
   - Do NOT modernize authentic archaic Andemta forms (`ሁነው`, `ሁኖ`, `ለኒህ`, `እኒህ`, `ደንጊያ`, `ኖሎት`, `አባግዕ`, `መጣፍ`, `አንጅል`, `፩ዱ`, `ከሥራ ሁለቱ`, `ከራቸሳው` if printed thus).
3. **Preserve Exact Line Break Boundaries**:
   - When fixing a word that wraps mid-word across two lines (`L_n` and `L_n+1`), keep the exact line split point as printed in the image!

=== REJOINED CONTINUOUS STREAM (FOR WORD & SENTENCE CONTEXT) ===
{rejoined_preview}

=== DRAFT PASS 1 LINE-BY-LINE TRANSCRIPTION TO AUDIT ===
{draft_text}
"""

def build_rejoined_preview(p_data: dict) -> str:
    blocks = []
    for col in p_data.get("columns", []):
        lines = col.get("lines", [])
        if not lines:
            continue
        s = []
        for i, ln in enumerate(lines):
            txt = ln.get("text", "").strip()
            tag = f"[L{ln['line_num']:02d}]"
            if i == 0:
                s.append(f"{tag} {txt}")
            else:
                if lines[i - 1].get("word_wraps_to_next_line", False):
                    s[-1] = s[-1] + f"↵{tag}" + txt
                else:
                    s.append(f"{tag} {txt}")
        blocks.append(f"--- Col {col['column_index']} Rejoined ---\n" + " ".join(s))
    return "\n\n".join(blocks)

def format_draft_for_prompt(p_data: dict) -> str:
    out = []
    for col in p_data.get("columns", []):
        out.append(f"=== Column {col['column_index']} ===")
        for ln in col.get("lines", []):
            wrap = "↵" if ln.get("word_wraps_to_next_line") else ""
            m = f"[{ln['margin_tag']}] " if ln.get("margin_tag") else ""
            out.append(f"L{ln['line_num']:02d}: {m}{ln['text']}{wrap}")
    return "\n".join(out)

async def test_verify(pdf_page: int):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    p_data = json.load(open(f"data/extracted/pages/page_{pdf_page:03d}.json", encoding="utf-8"))
    full_pil, crops, _ = prepare_3col_crops(pdf_page)
    draft_str = format_draft_for_prompt(p_data)
    rejoined_str = build_rejoined_preview(p_data)
    prompt = VERIFY_PROMPT.format(
        pdf_page=pdf_page,
        book_eth=p_data.get("book_page_ethiopic", ""),
        rejoined_preview=rejoined_str,
        draft_text=draft_str,
    )
    t0 = time.time()
    resp = await client.aio.models.generate_content(
        model="gemini-4-argon",
        contents=[full_pil, crops[0], crops[1], crops[2], prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PageVerificationResult,
            temperature=0.0,
        ),
    )
    dt = time.time() - t0
    res = json.loads(resp.text)
    print(f"\n=== Page {pdf_page} Verified in {dt:.1f}s ({len(res['corrections'])} corrections found) ===")
    for c in res["corrections"]:
        print(f"  Col {c['column_index']} L{c['line_num']:02d} [{c['visual_confusable_pair']}]:")
        print(f"    OLD: {c['old_text']}")
        print(f"    NEW: {c['corrected_text']}")
        print(f"    WHY: {c['reason']}")

async def main():
    await asyncio.gather(
        test_verify(1),
        test_verify(2),
        test_verify(3),
        test_verify(128),
    )

if __name__ == "__main__":
    asyncio.run(main())
