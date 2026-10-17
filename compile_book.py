import glob
import json
import os
import re
import sqlite3
from typing import Dict, List, Optional, Tuple

PAGES_DIR = "data/extracted/pages"
OUT_DIR = "data/extracted"
os.makedirs(OUT_DIR, exist_ok=True)

ETH_DIGIT_MAP = {
    "፩": 1, "፪": 2, "፫": 3, "፬": 4, "፭": 5, "፮": 6, "፯": 7, "፰": 8, "፱": 9,
    "፲": 10, "፳": 20, "፴": 30, "፵": 40, "፶": 50, "፷": 60, "፸": 70, "፹": 80, "፺": 90,
    "፻": 100, "፼": 10000,
}

ETHIOPIC_UNITS = ["", "፩", "፪", "፫", "፬", "፭", "፮", "፯", "፰", "፱"]
ETHIOPIC_TENS = ["", "፲", "፳", "፴", "፵", "፶", "፷", "፸", "፹", "፺"]

def int_to_ethiopic(n: int) -> str:
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
    # Strip non-ethiopic numeral characters except ወ (as in ፲ወ፪)
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

CHAPTER_RE = re.compile(r"ምዕራፍ[\s፡፥፤]*([፩-፼ወ]+)")

def rejoin_lines_text(lines: List[Dict]) -> str:
    """Rejoins diplomatic lines into continuous text, respecting word_wraps_to_next_line."""
    if not lines:
        return ""
    parts = []
    for i, ln in enumerate(lines):
        txt = ln.get("text", "").strip()
        if not txt:
            continue
        if i == 0:
            parts.append(txt)
        else:
            prev_wraps = lines[i - 1].get("word_wraps_to_next_line", False)
            # If previous line ended with ⟫ and current starts with ⟪ across a mid-word wrap, merge cleanly
            if prev_wraps:
                if parts and parts[-1].endswith("⟫") and txt.startswith("⟪"):
                    parts[-1] = parts[-1][:-1] + txt[1:]
                else:
                    parts[-1] = parts[-1] + txt
            else:
                parts.append(txt)
    return " ".join(parts)

def compile_all():
    page_files = sorted(glob.glob(os.path.join(PAGES_DIR, "page_*.json")))
    pages_by_num: Dict[int, Dict] = {}
    for pf in page_files:
        data = json.load(open(pf, encoding="utf-8"))
        pages_by_num[data["pdf_page"]] = data

    print(f"Loaded {len(pages_by_num)} extracted page files.")

    # 1. Extract 28-Chapter Index from Page 193
    chapter_index = []
    if 193 in pages_by_num:
        for entry in pages_by_num[193].get("toc_entries", []):
            ch_eth = entry.get("chapter_ethiopic") or ""
            ch_num = ethiopic_to_int(ch_eth) or entry.get("row_num")
            chapter_index.append({
                "chapter_num": ch_num,
                "chapter_ethiopic": int_to_ethiopic(ch_num),
                "geez_incipit": entry.get("geez_title", ""),
                "amharic_incipit": entry.get("amharic_title", ""),
            })

    # 2. Extract Topical Table of Contents (መክሥተ አርእስት) from Pages 195-200
    topical_index = []
    curr_toc_ch_eth = "፩"
    curr_toc_ch_num = 1
    for p in range(195, 201):
        if p not in pages_by_num:
            continue
        p_data = pages_by_num[p]
        for entry in p_data.get("toc_entries", []):
            raw_ch = entry.get("chapter_ethiopic")
            if raw_ch:
                parsed_ch = ethiopic_to_int(raw_ch)
                if parsed_ch and 1 <= parsed_ch <= 28:
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

    # 3. Walk Commentary Pages (1..192) to build Chapters, Verses, Diplomatic Lines, and Apparatus
    chapters_map: Dict[int, Dict] = {}
    all_uncertain: List[Dict] = []
    all_stage2_corrections: List[Dict] = []
    total_lines_count = 0

    curr_ch_num = 1
    curr_ch_eth = "፩"
    curr_v_num = 1
    curr_v_eth = "፩"
    curr_section_title: Optional[str] = None

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
                "verse_ethiopic": v_eth or int_to_ethiopic(v_num),
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

        # Collect uncertain flags and stage2 corrections across ALL pages
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
                txt = ln.get("text", "").strip()
                m_tag = ln.get("margin_tag")
                clean_txt = txt.replace("⟪", "").replace("⟫", "").strip()

                # Check if this line is a new chapter header (e.g. ምዕራፍ ፪ ።)
                ch_match = CHAPTER_RE.search(clean_txt)
                if (l_type == "chapter_title" or (ch_match and len(clean_txt) <= 18)) and ch_match:
                    new_ch = ethiopic_to_int(ch_match.group(1))
                    if new_ch and 1 <= new_ch <= 28:
                        curr_ch_num = new_ch
                        curr_ch_eth = int_to_ethiopic(new_ch)
                        curr_v_num = 1
                        curr_v_eth = "፩"
                        curr_section_title = None
                        ch_obj = ensure_chapter(curr_ch_num)
                        ch_obj["title_geez"] = clean_txt
                        ch_obj["start_pdf_page"] = p
                        ch_obj["start_book_page_ethiopic"] = book_eth
                        continue

                if l_type == "section_title":
                    curr_section_title = clean_txt

                # Check margin verse tag
                if m_tag:
                    m_clean = m_tag.strip()
                    # Ignore chapter margin tags
                    if not m_clean.startswith("ም"):
                        parsed_v = ethiopic_to_int(m_clean)
                        # Validate monotonic / reasonable verse number within chapter (1..80)
                        if parsed_v and 1 <= parsed_v <= 85:
                            # Guard against single-character OCR misread jumping backwards/forwards wildly
                            if parsed_v == curr_v_num or parsed_v == curr_v_num + 1 or (parsed_v > curr_v_num and parsed_v <= curr_v_num + 5) or (curr_v_num <= 2 and parsed_v <= 5):
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

    # 4. Finalize Chapters & Verses with rejoined continuous text and extracted Ge'ez root lemmas
    chapters_list = []
    total_verses_count = 0
    for ch_num in sorted(chapters_map.keys()):
        ch_obj = chapters_map[ch_num]
        v_list = []
        for v_num in sorted(ch_obj["verses_map"].keys()):
            v_obj = ch_obj["verses_map"][v_num]
            rejoined = rejoin_lines_text(v_obj["lines"])
            # Extract Ge'ez root segments wrapped in ⟪...⟫
            geez_lemmas = [m.strip() for m in re.findall(r"⟪([^⟫]+)⟫", rejoined) if m.strip()]
            plain_rejoined = rejoined.replace("⟪", "").replace("⟫", "")
            # Split commentary by አንድም for structured sub-interpretations
            v_obj["rejoined_marked_text"] = rejoined
            v_obj["rejoined_plain_text"] = plain_rejoined
            v_obj["geez_root_lemmas"] = geez_lemmas
            v_list.append(v_obj)
            total_verses_count += 1
        del ch_obj["verses_map"]
        ch_obj["verses"] = v_list
        chapters_list.append(ch_obj)

    master_book = {
        "title_geez": "የጌታችን የኢየሱስ ክርስቶስ ቅዱስ ወንጌል ። ቅዱስ ማቴዎስ እንደ ጻፈው ።",
        "title_english": "The Holy Gospel of Our Lord Jesus Christ According to St. Matthew — Traditional Ge'ez & Amharic Andemta Commentary (ወንጌለ ማቴዎስ አንድምታ ትርጓሜ)",
        "stats": {
            "total_pdf_pages": 200,
            "extracted_pages_count": len(pages_by_num),
            "total_chapters": len(chapters_list),
            "total_verses": total_verses_count,
            "total_diplomatic_lines": total_lines_count,
            "total_topical_index_entries": len(topical_index),
            "total_stage2_corrections": len(all_stage2_corrections),
            "total_uncertain_apparatus_flags": len(all_uncertain),
        },
        "chapter_index": chapter_index,
        "topical_index": topical_index,
        "chapters": chapters_list,
        "stage2_corrections": all_stage2_corrections,
        "uncertain_apparatus": all_uncertain,
    }

    master_json_path = os.path.join(OUT_DIR, "matewes_andemta_complete.json")
    with open(master_json_path, "w", encoding="utf-8") as f:
        json.dump(master_book, f, ensure_ascii=False, indent=2)

    # 5. Build SQLite database with FTS5 search
    db_path = os.path.join(OUT_DIR, "matewes_andemta.db")
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
        CREATE TABLE uncertain_apparatus (
            id INTEGER PRIMARY KEY,
            pdf_page INTEGER,
            book_page_ethiopic TEXT,
            column_index INTEGER,
            line_num INTEGER,
            line_text TEXT,
            printed_text TEXT,
            alternative TEXT,
            note TEXT
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

    for u in all_uncertain:
        cur.execute(
            "INSERT INTO uncertain_apparatus VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (u["id"], u["pdf_page"], u["book_page_ethiopic"], u["column_index"], u["line_num"], u["line_text"], u["printed_text"], u["alternative"], u["note"])
        )

    conn.commit()
    conn.close()

    # 6. Export Reader Markdown & Diplomatic Markdown
    reader_md_path = os.path.join(OUT_DIR, "matewes_andemta_reader.md")
    with open(reader_md_path, "w", encoding="utf-8") as f:
        f.write(f"# {master_book['title_geez']}\n\n")
        for ch in chapters_list:
            f.write(f"## ምዕራፍ {ch['chapter_ethiopic']} ({ch['chapter_num']}) — {ch.get('geez_incipit', '')}\n\n")
            for v in ch["verses"]:
                if v.get("section_title"):
                    f.write(f"### {v['section_title']}\n\n")
                formatted = v["rejoined_marked_text"].replace("⟪", "**").replace("⟫", "**")
                f.write(f"**[{ch['chapter_ethiopic']}፥{v['verse_ethiopic']}]** *(ገጽ {v['start_book_page_ethiopic']})* {formatted}\n\n")

    diplomatic_md_path = os.path.join(OUT_DIR, "matewes_andemta_diplomatic.md")
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

    print("Compiled outputs:")
    print(f"  • JSON: {master_json_path}")
    print(f"  • SQLite DB: {db_path}")
    print(f"  • Reader Markdown: {reader_md_path}")
    print(f"  • Diplomatic Markdown: {diplomatic_md_path}")
    print(f"  • Stats: {json.dumps(master_book['stats'], indent=2)}")

if __name__ == "__main__":
    compile_all()
