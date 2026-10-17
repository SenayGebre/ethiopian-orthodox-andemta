import asyncio
import glob
import json
import os
import sys
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from extract_all_pages import prepare_3col_crops, prepare_toc_crops
import compile_book

load_dotenv()

PAGES_DIR = "data/extracted/pages"
VERIFY_DIR = "data/extracted/verified_logs"
os.makedirs(VERIFY_DIR, exist_ok=True)

class LineCorrection(BaseModel):
    column_index: int
    line_num: int
    old_text: str = Field(description="Exact text of this line from Draft Pass 1")
    corrected_text: str = Field(description="Corrected text of this line preserving exact line break boundaries and ⟪...⟫ tags")
    word_wraps_to_next_line: bool = Field(description="True if the word at the end of this line continues mid-word onto the next line")
    visual_confusable_pair: str = Field(description="The visually confusable characters involved, e.g. 'ሺ -> ቢ', 'ሩ -> ራ', 'ዘርአ -> ዘርእ', 'ለ፰ -> ለ፷', 'ምን -> ንጐ', 'ገዮ -> ዣ'")
    reason: str = Field(description="Concise philological (Ge'ez/Amharic) and visual explanation")

class PageVerificationResult(BaseModel):
    corrections: List[LineCorrection]

VERIFY_PROMPT = """You are a Senior Ethiopian Orthodox Yeneta (የኔታ / መምህር — Master Scholar of Classical Ge'ez [ልሳነ ግዕዝ] and Traditional Wengel Andemta Commentary [ወንጌለ ማቴዎስ አንድምታ ትርጓሜ]).

We ran an initial OCR pass (Draft Pass 1) on PDF Page {pdf_page} (Book Page {book_eth}).
Because this is an old lead-type printed book photographed with a phone camera, ink bleed, smudges, and faint serifs frequently make one Ethiopic Fidel look like another visually similar Fidel.

Your task is to audit EVERY SINGLE LINE of PDF Page {pdf_page} by comparing the Draft Pass 1 text against:
1. The 2x zoomed column/section images and full page image provided, AND
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
     * e.g., Ge'ez active participle `ከዓዌ ዘርእ` misread as `ክዓዊ ዘርእ`,
     * e.g., Ge'ez `፩ መሐስዓ` misread as `፩ ማሕስዓ`,
     * e.g., Ge'ez `ጸሐፍዎ ለብእሲ` misread as `ጸሐፈዮ ለብእሲ`,
     * e.g., Amharic `የማዘን` (`የማዘን ደግነት ነው`) misread as `የሚዘን`, `ባየች` misread as `በየች`, `ሞተችበት` misread as `ሞታችበት`, `መሄድ`/`ሄዳለች` misread as `መሂድ`/`ሂዳለች`.
   - Wide-glyph or split-glyph misreads across line wraps: e.g., `መ↵ያዣ` where wide `ዣ` was misread as `ገዮ` (`ያገዮ`), or `ያ↵መጣል` where `ጣ` was misread as `ጻ` (`መጻል`).
   - Base-shape lookalikes: `ደ`/`ይ`, `ን`/`ጎ`, `ዐ`/`ዓ`/`ዕ`/`አ`/`እ`, `ኀ`/`ነ`/`ከ`/`ገ`, `ጸ`/`ፀ`/`ዘ`, `ሐ`/`ሕ`, `ወ`/`መ`, `ረ`/`ፈ`, `ቀ`/`ተ`, `ሥ`/`ሠ`.
   - Ethiopic numeral & underline lookalikes: `፷` (60) misread as `፰` (8) (e.g. `ለ፶ ለ፷`), `፴፩` vs `፳፩`, `፵` (40) vs `ም`, or reference underlines misread as `ዑ`.
2. **STRICT VISUAL GROUNDING — NO UNRELATED SYNONYM GUESSING**:
   - ONLY correct a character when the printed glyph in the zoomed image actually supports the corrected Fidel (i.e. it is a visual lookalike / ink-bleed / vowel-order / spacing error, or a genuine misread of the image).
   - NEVER replace a clearly printed word (such as `አለ`) with a visually unrelated word (such as `ተወ`) if the printed letters in the image are clearly `አለ`!
   - Do NOT modernize authentic archaic Andemta forms (`ሁነው`, `ሁኖ`, `ለኒህ`, `እኒህ`, `ደንጊያ`, `ኖሎት`, `አባግዕ`, `መጣፍ`, `አንጅል`, `፩ዱ`, `ከሥራ ሁለቱ`).
3. **Preserve Exact Line Break Boundaries**:
   - When fixing a word that wraps mid-word across two lines (`L_n` and `L_n+1`), keep the exact line split point as printed in the image!

=== CROSS-PAGE BOUNDARY CONTEXT ===
Previous Page Ending: {prev_tail}
Next Page Beginning: {next_head}

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

def get_neighbor_context(pdf_page: int) -> tuple[str, str]:
    prev_tail = "(Start of Book)"
    next_head = "(End of Section)"
    prev_path = os.path.join(PAGES_DIR, f"page_{pdf_page-1:03d}.json")
    next_path = os.path.join(PAGES_DIR, f"page_{pdf_page+1:03d}.json")
    if os.path.exists(prev_path):
        pd = json.load(open(prev_path, encoding="utf-8"))
        cols = pd.get("columns", [])
        if cols and cols[-1].get("lines"):
            tail_lns = cols[-1]["lines"][-2:]
            prev_tail = " ".join(l.get("text", "") + ("↵" if l.get("word_wraps_to_next_line") else "") for l in tail_lns)
    if os.path.exists(next_path):
        nd = json.load(open(next_path, encoding="utf-8"))
        cols = nd.get("columns", [])
        if cols and cols[0].get("lines"):
            head_lns = cols[0]["lines"][:2]
            next_head = " ".join(l.get("text", "") for l in head_lns)
    return prev_tail, next_head

async def verify_single_page(client: genai.Client, pdf_page: int, sem: asyncio.Semaphore, force: bool = False):
    log_path = os.path.join(VERIFY_DIR, f"verify_{pdf_page:03d}.json")
    page_path = os.path.join(PAGES_DIR, f"page_{pdf_page:03d}.json")

    if not os.path.exists(page_path):
        return {"pdf_page": pdf_page, "status": "missing"}

    if os.path.exists(log_path) and not force:
        return {"pdf_page": pdf_page, "status": "cached"}

    p_data = json.load(open(page_path, encoding="utf-8"))
    p_type = p_data.get("page_type", "")
    if p_type in ("blank", "illustration"):
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({"pdf_page": pdf_page, "corrections": []}, f, ensure_ascii=False, indent=2)
        return {"pdf_page": pdf_page, "status": "skipped"}

    async with sem:
        for attempt in range(5):
            try:
                t0 = time.time()
                prev_tail, next_head = get_neighbor_context(pdf_page)
                draft_str = format_draft_for_prompt(p_data)
                rejoined_str = build_rejoined_preview(p_data)
                prompt = VERIFY_PROMPT.format(
                    pdf_page=pdf_page,
                    book_eth=p_data.get("book_page_ethiopic", ""),
                    prev_tail=prev_tail,
                    next_head=next_head,
                    rejoined_preview=rejoined_str,
                    draft_text=draft_str,
                )

                if p_type == "commentary_3col":
                    full_pil, crops, _ = prepare_3col_crops(pdf_page)
                    contents = [full_pil, crops[0], crops[1], crops[2], prompt]
                else:
                    full_pil, top_pil, bot_pil = prepare_toc_crops(pdf_page)
                    contents = [full_pil, top_pil, bot_pil, prompt]

                resp = await client.aio.models.generate_content(
                    model="gemini-4-argon",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=PageVerificationResult,
                        temperature=0.0,
                    ),
                )
                dt = time.time() - t0
                res = json.loads(resp.text)
                corrections = res.get("corrections", [])

                # Apply corrections to page_XXX.json
                applied_count = 0
                col_map = {c["column_index"]: c for c in p_data.get("columns", [])}
                for corr in corrections:
                    c_obj = col_map.get(corr["column_index"])
                    if not c_obj:
                        continue
                    for ln in c_obj.get("lines", []):
                        if ln.get("line_num") == corr["line_num"]:
                            old_txt = ln.get("text", "")
                            new_txt = corr["corrected_text"].strip()
                            if new_txt and old_txt != new_txt:
                                ln["stage1_text"] = ln.get("stage1_text", old_txt)
                                ln["text"] = new_txt
                                ln["word_wraps_to_next_line"] = corr.get("word_wraps_to_next_line", ln.get("word_wraps_to_next_line", False))
                                ln["stage2_correction"] = {
                                    "pair": corr.get("visual_confusable_pair", ""),
                                    "reason": corr.get("reason", ""),
                                }
                                # Clear resolved uncertain flags if fixed
                                ln["uncertain"] = []
                                applied_count += 1
                            break

                p_data["stage2_verified"] = True
                p_data["stage2_corrections_count"] = applied_count
                with open(page_path, "w", encoding="utf-8") as f:
                    json.dump(p_data, f, ensure_ascii=False, indent=2)

                log_payload = {
                    "pdf_page": pdf_page,
                    "book_page_ethiopic": p_data.get("book_page_ethiopic"),
                    "elapsed_sec": round(dt, 1),
                    "applied_count": applied_count,
                    "corrections": corrections,
                }
                with open(log_path, "w", encoding="utf-8") as f:
                    json.dump(log_payload, f, ensure_ascii=False, indent=2)

                print(f"🔍 Verified Page {pdf_page:3d} ({p_data.get('book_page_ethiopic')}): {dt:.1f}s | fixed {applied_count} lines", flush=True)
                return log_payload
            except Exception as e:
                wait = 6 * (attempt + 1)
                print(f"⚠️ Verify Page {pdf_page:3d} attempt {attempt+1} error: {e}. Waiting {wait}s...", flush=True)
                await asyncio.sleep(wait)

        print(f"❌ Verify Page {pdf_page:3d} FAILED after 5 attempts", flush=True)
        return {"pdf_page": pdf_page, "status": "failed"}

async def main():
    if len(sys.argv) > 1:
        pages = []
        for arg in sys.argv[1:]:
            if "-" in arg:
                a, b = arg.split("-")
                pages.extend(range(int(a), int(b) + 1))
            else:
                pages.append(int(arg))
    else:
        pages = list(range(1, 201))

    concurrency = int(os.environ.get("VERIFY_CONCURRENCY", "10"))
    sem = asyncio.Semaphore(concurrency)
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    print(f"Starting Stage-2 Yeneta Philological & Visual Verification across {len(pages)} pages (concurrency={concurrency})...", flush=True)
    t0 = time.time()
    await asyncio.gather(*(verify_single_page(client, p, sem) for p in pages))
    print(f"🎉 Stage-2 Verification completed in {time.time() - t0:.1f}s! Recompiling corpus...", flush=True)
    compile_book.compile_all()

    # Summarize all corrections across the entire book
    all_logs = sorted(glob.glob(os.path.join(VERIFY_DIR, "verify_*.json")))
    total_fixed = 0
    master_log = []
    for lp in all_logs:
        ld = json.load(open(lp, encoding="utf-8"))
        total_fixed += ld.get("applied_count", 0)
        if ld.get("corrections"):
            master_log.append(ld)
    with open("data/extracted/stage2_corrections_log.json", "w", encoding="utf-8") as f:
        json.dump({"total_pages_verified": len(all_logs), "total_lines_corrected": total_fixed, "pages": master_log}, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved master correction log: {total_fixed} total lines corrected across {len(all_logs)} pages.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
