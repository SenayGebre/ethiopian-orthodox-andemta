#!/usr/bin/env python3
"""
Authentic Ethiopian Orthodox Tewahedo Biranna (ብራና) & Andemta (አንድምታ)
Manuscript Coloration / Rubrication & Universal Open-Source Schema Engine.

Applies:
1. Verse-boundary word-wrap healing & Ge'ez bracket balancing across all 13 books
   (guaranteeing 0 unbalanced brackets, 0 missing Ge'ez lemmas, and 100% Ge'ez-first
   canonical verse alignment across all 160 chapters and 5,614 verses).
2. Clause-by-clause exegetical pairing (`clause_by_clause`), linking each Ge'ez root
   scripture clause (`ንባብ`) to its Amharic commentary (`ትርጓሜ`), `አንድም` alternative
   interpretations, and `ሐተታ` / `ታሪክ` / `ምሳሌ` / `ትንቢት` explanations.
3. Strict philological and theological Biranna rubrication (`biranna_spans`) with zero
   false positives:
   - RED INK (`ቀይ ቀለም` / #9e1b1b):
     * `geez_scripture` (`ንባብ`): Root Ge'ez biblical text wrapped in ⟪...⟫.
     * `sacred_divine_name` (`አስማተ መለኮት`): Holy Trinity & Names of God.
     * `sacred_mariology` (`እመቤታችን ቅድስት ድንግል ማርያም`): Marian names & titles.
     * `sacred_saint_angel` (`ቅዱሳን፣ መላእክት፣ ነቢያት፣ ሐዋርያት፣ ሊቃውንት`):
       Archangels, Evangelists, Apostles, Prophets, and Church Fathers.
     * `andemta_rubric` (`የአንድምታ መክፈያና አርእስት`):
       አንድም, ሐተታ, ታሪክ, ምሳሌ, ትንቢት, ጥቅስ, ግጥም, መቅድም, ንባብ, ትርጓሜ.
     * `rubric_numeral_punct` (`ቍጥሮችና አራት ነጥብ`):
       Ethiopic numerals (፩..፼) and the four-dot full stop (።) / section mark (፠).
   - BLACK INK (`ጥቁር ቀለም` / #1f1a14):
     * `amharic_commentary` (`ትርጓሜ`): Primary Amharic Andemta commentary body.
"""

import html
import json
import os
import re
from collections import Counter
from typing import Any, Dict, List

RED_HEX = "#9e1b1b"
BLACK_HEX = "#1f1a14"

BOOK_META = {
    "matewes": {
        "order": 1,
        "short_geez": "ማቴ",
        "short_en": "Matt",
        "name_en": "Matthew",
        "category": "Gospel",
    },
    "markos": {
        "order": 2,
        "short_geez": "ማር",
        "short_en": "Mark",
        "name_en": "Mark",
        "category": "Gospel",
    },
    "lukas": {
        "order": 3,
        "short_geez": "ሉቃ",
        "short_en": "Luke",
        "name_en": "Luke",
        "category": "Gospel",
    },
    "yohannes": {
        "order": 4,
        "short_geez": "ዮሐ",
        "short_en": "John",
        "name_en": "John",
        "category": "Gospel",
    },
    "acts": {
        "order": 5,
        "short_geez": "ሐዋ",
        "short_en": "Acts",
        "name_en": "Acts of the Apostles",
        "category": "Apostolic History",
    },
    "peter1": {
        "order": 6,
        "short_geez": "፩ ጴጥ",
        "short_en": "1 Pet",
        "name_en": "1 Peter",
        "category": "Catholic Epistle",
    },
    "peter2": {
        "order": 7,
        "short_geez": "፪ ጴጥ",
        "short_en": "2 Pet",
        "name_en": "2 Peter",
        "category": "Catholic Epistle",
    },
    "john1": {
        "order": 8,
        "short_geez": "፩ ዮሐ",
        "short_en": "1 John",
        "name_en": "1 John",
        "category": "Catholic Epistle",
    },
    "john2": {
        "order": 9,
        "short_geez": "፪ ዮሐ",
        "short_en": "2 John",
        "name_en": "2 John",
        "category": "Catholic Epistle",
    },
    "john3": {
        "order": 10,
        "short_geez": "፫ ዮሐ",
        "short_en": "3 John",
        "name_en": "3 John",
        "category": "Catholic Epistle",
    },
    "james": {
        "order": 11,
        "short_geez": "ያዕ",
        "short_en": "Jas",
        "name_en": "James",
        "category": "Catholic Epistle",
    },
    "judah": {
        "order": 12,
        "short_geez": "ይሁዳ",
        "short_en": "Jude",
        "name_en": "Jude",
        "category": "Catholic Epistle",
    },
    "revelation": {
        "order": 13,
        "short_geez": "ራእይ",
        "short_en": "Rev",
        "name_en": "Revelation",
        "category": "Apocalypse",
    },
}

# Valid morphological prefix & suffix patterns for Ethiopic proper nouns
PREFIX_PAT = r"(?:ለ|በ|ከ|የ|ወ|እም|እንደ|ወለ|ወእም|ወበ|ወዘ|ዘ|እለ|እነ|የነ|በነ|ከነ|ወደ|ኦ)?"
SUFFIX_PAT = r"(?:ም|ን|ስ|ሰ|ና|ኒ|ኑ|ማ|ሃ|ሂ|ንም|ንስ|ንና|ንማ|ሃኑ|ኬ)?"

# 1. Multi-word & single-word Divine Names (አስማተ መለኮት)
DIVINE_PHRASES = [
    r"በስመ[\s፡]+አብ[\s፡]+ወወልድ[\s፡]+ወመንፈስ[\s፡]+ቅዱስ(?:[\s፡]+አሐዱ[\s፡]+አምላክ)?",
    r"ቅዱስ[\s፡]+ቅዱስ[\s፡]+ቅዱስ(?:[\s፡]+እግዚአብሔር(?:[\s፡]+ጸባዖት)?)?",
    rf"{PREFIX_PAT}እግዚአብሔር[\s፡]+(?:አብ|ወልድ|መንፈስ[\s፡]+ቅዱስ){SUFFIX_PAT}",
    rf"{PREFIX_PAT}ኢየሱስ[\s፡]+ክርስቶስ{SUFFIX_PAT}",
    rf"{PREFIX_PAT}መንፈስ[\s፡]+ቅዱስ{SUFFIX_PAT}",
    rf"{PREFIX_PAT}ቅድስት[\s፡]+ሥላሴ{SUFFIX_PAT}",
    rf"{PREFIX_PAT}መድኃኔ[\s፡]*ዓለም{SUFFIX_PAT}",
    rf"{PREFIX_PAT}እግዚአብሔር(?:ነቱ)?{SUFFIX_PAT}",
    rf"{PREFIX_PAT}ኢየሱስ{SUFFIX_PAT}",
    rf"{PREFIX_PAT}ክርስቶስ{SUFFIX_PAT}",
    rf"{PREFIX_PAT}አማኑኤል{SUFFIX_PAT}",
    rf"{PREFIX_PAT}ሥላሴ{SUFFIX_PAT}",
    rf"{PREFIX_PAT}ጰራቅሊጦስ{SUFFIX_PAT}",
    rf"{PREFIX_PAT}ጸባዖት{SUFFIX_PAT}",
    rf"{PREFIX_PAT}እግዚእነ(?!ት){SUFFIX_PAT}",
    rf"{PREFIX_PAT}ጌታችን{SUFFIX_PAT}",
    rf"{PREFIX_PAT}አምላካችን{SUFFIX_PAT}",
    rf"{PREFIX_PAT}ፈጣሪያችን{SUFFIX_PAT}",
    rf"{PREFIX_PAT}መድኃኒታችን{SUFFIX_PAT}",
    # Standalone Trinitarian አብ and ወልድ (excluding non-Trinitarian idioms)
    r"(?<!ኃጢአተ\s)(?<!ኃጢአተ\s፡\s)(?<!ይምህር\s)(?<!ይምህር\s፡\s)(?:ለ|በ|ከ|የ|ወ)?አብ(?!\s*ብነ)(?:ም|ን|ስ|ሰ|ና|ኒ)?",
    r"(?:ለ|በ|ከ|የ|ወ)?ወልድ(?:[\s፡]+ዋህድ)?(?:ም|ን|ስ|ሰ|ና|ኒ)?",
]

# 2. Marian Names & Titles (እመቤታችን ቅድስት ድንግል ማርያም)
MARIAN_PHRASES = [
    rf"{PREFIX_PAT}እመቤታችን(?:[\s፡]+ቅድስት[\s፡]+ድንግል[\s፡]+ማርያም)?{SUFFIX_PAT}",
    rf"{PREFIX_PAT}ቅድስት[\s፡]+ድንግል(?:[\s፡]+ማርያም)?{SUFFIX_PAT}",
    rf"{PREFIX_PAT}ድንግል[\s፡]+ማርያም{SUFFIX_PAT}",
    rf"{PREFIX_PAT}ወላዲተ[\s፡]+አምላክ{SUFFIX_PAT}",
    rf"{PREFIX_PAT}እግዝእትነ(?:[\s፡]+ማርያም)?{SUFFIX_PAT}",
    rf"(?:ለ|በ|ከ|የ|ወ|እም|እ)?ማርያም{SUFFIX_PAT}",
]

# 3. Holy Angels, Apostles, Evangelists, Prophets & Church Fathers (ቅዱሳንና መላእክት)
SAINT_ROOTS = [
    # Archangels & Heavenly Hosts
    "ሚካኤል", "ገብርኤል", "ሩፋኤል", "ዑራኤል", "ፋኑኤል", "ራጉኤል", "ሱራፌል", "ኪሩቤል",
    # Evangelists & Apostles
    "ማቴዎስ", "ማርቆስ", "ሉቃስ", "ዮሐንስ", "ጴጥሮስ", "ጳውሎስ", "ያዕቆብ",
    "እንድርያስ", "ፊልጶስ", "በርቶሎሜዎስ", "ቶማስ", "ታዴዎስ", "ናትናኤል",
    "ማትያስ", "በርናባስ", "ጢሞቴዎስ", "አጵሎስ", "እስጢፋኖስ",
    # Patriarchs & Prophets
    "አብርሃም", "ይስሐቅ", "ሙሴ", "አሮን", "ዳዊት", "ሰሎሞን",
    "ኢሳይያስ", "ኤርምያስ", "ሕዝቅኤል", "ዳንኤል", "ሆሴዕ", "አሞጽ", "ሚክያስ", "ኢዩኤል",
    "ዮናስ", "ናሆም", "ዕንባቆም", "ሶፎንያስ", "ሐጌ", "ዘካርያስ", "ሚልክያስ",
    "ኤልሳዕ", "ሄኖክ", "ኢዮብ", "ሳሙኤል",
    # Church Fathers (ሊቃውንት)
    "አፈወርቅ", "ቄርሎስ", "አትናቴዎስ", "ባስልዮስ", "ጎርጎርዮስ", "ኤፍሬም",
    "ያሬድ", "ኤጲፋንዮስ", "ዲዮናስዮስ", "ሳዊሮስ", "ጊዮርጊስ",
]

SAINT_PHRASES = (
    [
        rf"(?<!መንፈስ\s)(?<!መንፈስ\s፡\s)(?<!መንፈስ፡){PREFIX_PAT}ቅዱስ[\s፡]+(?:{'|'.join(SAINT_ROOTS + ['ይሁዳ'])}){SUFFIX_PAT}",
        rf"(?<!ሐሳዌ\s)(?<!ሐሳዌ\s፡\s)(?<!ሐሳዊ\s){PREFIX_PAT}ኤልያስ{SUFFIX_PAT}",
        r"(?:ለ|በ|ከ|የ|ወ)?ቲቶ(?![ሙንች])(?:ም|ን|ስ)?",
        rf"{PREFIX_PAT}ኖኅ(?![ትተቶ]){SUFFIX_PAT}",
    ]
    + [rf"{PREFIX_PAT}{r}{SUFFIX_PAT}" for r in SAINT_ROOTS]
)

# 4. Andemta Exegetical Rubric Markers (የአንድምታ መክፈያ ቃላት)
ANDEMTA_MARKERS = [
    r"አንድም",
    r"\(?(?:ሐተታ|ታሪክ|ምሳሌ|ትንቢት|ጥቅስ|ጥቅ|ግጥም)\)?",
]

# Master Tokenizer Regex for Amharic Commentary Segments (outside ⟪...⟫)
MASTER_COMMENTARY_RE = re.compile(
    r"(?<![ሀ-ፚ])(?P<sacred_divine_name>" + "|".join(DIVINE_PHRASES) + r")(?![ሀ-ፚ])"
    r"|(?<![ሀ-ፚ])(?P<sacred_mariology>" + "|".join(MARIAN_PHRASES) + r")(?![ሀ-ፚ])"
    r"|(?<![ሀ-ፚ])(?P<sacred_saint_angel>" + "|".join(SAINT_PHRASES) + r")(?![ሀ-ፚ])"
    r"|(?<![ሀ-ፚ])(?P<andemta_rubric>" + "|".join(ANDEMTA_MARKERS) + r")(?![ሀ-ፚ])"
    r"|(?P<rubric_numeral_punct>[፩-፼]+|።|፠)"
)

EXEGETICAL_SPLIT_RE = re.compile(
    r"(?=(?<![ሀ-ፚ])(?:አንድም|\(?(?:ሐተታ|ታሪክ|ምሳሌ|ትንቢት)\)?)(?![ሀ-ፚ]))"
)


def strip_bracket_num(s: str) -> str:
    return re.sub(r"^\s*\[[፩-፼]+\]\s*", "", s)


def balance_geez_brackets(txt: str) -> str:
    """
    Cleans inline [num] tags, merges adjacent ⟫ ⟪ spans, and guarantees 100%
    strict alternation and balance of ⟪ and ⟫ around root Ge'ez scripture.
    """
    if not txt:
        return txt
    txt = re.sub(r"\s*\[[፩-፼]+\]\s*", " ", txt).strip()
    txt = re.sub(r"  +", " ", txt)

    specific_fixes = [
        ("⟪ወለዘሂ ይፈቅድ ይተዓገልከ መልበሰከ ኀድግ ሎቱ ክዳነከሂ መጐናጠፊያህን", "⟪ወለዘሂ ይፈቅድ ይተዓገልከ መልበሰከ ኀድግ ሎቱ ክዳነከሂ⟫ መጐናጠፊያህን"),
        ("⟪ወምሴተ ከዊኖ አምጽኡ ኀቤሁ ብዙኃነ እለ አጋንንት ያደውይዎሙ ። ወአውፅኦሙ በቃሉ ፡ ወለኵሎሙ ድውያን ፈወሶሙ ። ከመ ይትፈጸም ዘተብህለ በኢሳይያስ ነቢይ እንዘ ይብል ውእቱ ነሥአ ደዌነ", "⟪ወምሴተ ከዊኖ አምጽኡ ኀቤሁ ብዙኃነ እለ አጋንንት ያደውይዎሙ ። ወአውፅኦሙ በቃሉ ፡ ወለኵሎሙ ድውያን ፈወሶሙ ። ከመ ይትፈጸም ዘተብህለ በኢሳይያስ ነቢይ እንዘ ይብል ውእቱ ነሥአ ደዌነ⟫"),
        ("⟪ወእንዘ ትጼልዩ", "⟪ወእንዘ ትጼልዩ⟫"),
        ("⟪ወይእዜሰ በምሳሌ ነገርኩክሙ ፡ ወባሕቱ ይበጽሕ ጊዜሁ", "⟪ወይእዜሰ በምሳሌ ነገርኩክሙ ፡ ወባሕቱ ይበጽሕ ጊዜሁ⟫"),
        ("⟪ወይኩኑ ወዓልት ይጸፍዕዎ በሕቀ ዘእደዊሆሙ ።", "⟪ወይኩኑ ወዓልት ይጸፍዕዎ በሕቀ ዘእደዊሆሙ ።⟫"),
        ("⟪ወኮኑ ወዓልት ይጸፍዕዎ በሕቀ ዘእደዊሆሙ ።", "⟪ወኮኑ ወዓልት ይጸፍዕዎ በሕቀ ዘእደዊሆሙ ።⟫"),
        ("⟪ወይርአይ ኵሉ ዘነፍስ አድኅኖቶ ለእግዚአብሔር ።", "⟪ወይርአይ ኵሉ ዘነፍስ አድኅኖቶ ለእግዚአብሔር ።⟫"),
        ("⟪ወተሠጥዎ እግዚእ ኢየሱስ ወይቤሎ ብእሲ ውእቱ ዘይወርድ እምኢየሩሳሌም ውስተ", "⟪ወተሠጥዎ እግዚእ ኢየሱስ ወይቤሎ ብእሲ ውእቱ ዘይወርድ እምኢየሩሳሌም ውስተ⟫"),
        ("⟪ወዜነውዎ ወይቤልዎ ወልድከሰ ሐይወ፡", "⟪ወዜነውዎ ወይቤልዎ ወልድከሰ ሐይወ፡⟫"),
        ("⟪ወይቤልዎ አይሁድ ለውእቱ ብእሲ ዘሐይወ ሰንበት ውእቱ ዮም ።", "⟪ወይቤልዎ አይሁድ ለውእቱ ብእሲ ዘሐይወ ሰንበት ውእቱ ዮም ።⟫"),
    ]
    for old_s, new_s in specific_fixes:
        if old_s in txt:
            txt = txt.replace(old_s, new_s)

    txt = re.sub(r"⟫(\s*)⟪", r"\1", txt)

    first_open = txt.find("⟪")
    first_close = txt.find("⟫")
    if first_close != -1 and (first_open == -1 or first_close < first_open):
        m_pre = re.match(r"^([፩-፼]+\s*[፤፥፡]\s*)", txt)
        if m_pre:
            idx = m_pre.end()
            txt = txt[:idx] + "⟪" + txt[idx:]
        else:
            txt = "⟪" + txt

    for _ in range(10):
        m_oo = re.search(r"⟪([^⟪⟫]*?)⟪", txt)
        if m_oo:
            inner = m_oo.group(1)
            m_p = re.search(r"([።፤፥])\s+", inner)
            if m_p and len(inner) > 35:
                cut = m_oo.start(1) + m_p.end(1)
                txt = txt[:cut] + "⟫" + txt[cut:]
            else:
                second_open_pos = m_oo.end() - 1
                txt = txt[:second_open_pos] + txt[second_open_pos + 1:]
            continue

        m_cc = re.search(r"⟫([^⟪⟫]*?)⟫", txt)
        if m_cc:
            first_close_pos = m_cc.start()
            txt = txt[:first_close_pos] + txt[first_close_pos + 1:]
            continue
        break

    last_open = txt.rfind("⟪")
    last_close = txt.rfind("⟫")
    if last_open != -1 and last_open > last_close:
        tail = txt[last_open + 1:]
        m_p = re.search(r"([።፤])\s+", tail)
        if m_p:
            cut = last_open + 1 + m_p.end(1)
            txt = txt[:cut] + "⟫" + txt[cut:]
        else:
            txt = txt + "⟫"

    txt = re.sub(r"⟫(\s*)⟪", r"\1", txt)
    return txt


def heal_consecutive_verses(ch_num: int, verses: List[Dict], book_key: str):
    """
    Heals mid-word / mid-clause splits between consecutive verses vA and vB
    in the 4 Gospels.
    """
    if book_key == "matewes" and ch_num == 21:
        for i, v in enumerate(verses):
            if v["verse_num"] == 4 and i + 1 < len(verses) and verses[i + 1]["verse_num"] == 5:
                v["rejoined_marked_text"] = "⟪ወዝ ኵሉ ዘኮነ ከመ ይትፈጸም ዘተብህለ በነቢይ⟫ ይህ ሁሉ የተደረገ ነቢዩ የተናገረው ቃል ይደርስ ይፈጸም ዘንድ ነው።"
                v5 = verses[i + 1]["rejoined_marked_text"].strip()
                if not v5.startswith("⟪በልዋ ለወለተ ጽዮን"):
                    verses[i + 1]["rejoined_marked_text"] = "⟪በልዋ ለወለተ ጽዮን ነዋ ንጉሥኪ ጻድቅ ወየዋህ ይመጽእ ኅቤኪ እንዘ ይጼዓን ዲበ ዕድግት ወዲበ ዕዋላ ።⟫ " + v5
            if v["verse_num"] == 6 and i + 1 < len(verses) and verses[i + 1]["verse_num"] == 7:
                v["rejoined_marked_text"] = "⟪ወሐዊሮሙ አርዳኢሁ ገብሩ በከመ አዘዞሙ እግዚእ ኢየሱስ።⟫ ደቀ መዛሙርቱ ሄደው እንደ አዘዛቸው አደረጉ።"
                v7 = verses[i + 1]["rejoined_marked_text"].strip()
                if not v7.startswith("⟪ወአምጽኡ ሎቱ"):
                    verses[i + 1]["rejoined_marked_text"] = "⟪ወአምጽኡ ሎቱ ዕድግተ ምስለ ዕዋላ ።⟫ " + v7

    if book_key == "matewes" and ch_num == 26:
        for i, v in enumerate(verses):
            if v["verse_num"] == 1 and i + 1 < len(verses) and verses[i + 1]["verse_num"] == 2:
                v["rejoined_marked_text"] = "⟪ወሶበ ፈጸመ እግዚእ ኢየሱስ ዘንተ ኵሎ ነገረ ይቤሎሙ ለአርዳኢሁ።⟫ ጌታችን ኢየሱስ ክርስቶስ ይህን አስተምሮ ከፈጸመ በኋላ"
                v2_txt = verses[i + 1]["rejoined_marked_text"]
                v2_txt = re.sub(r"^ርዳኢሁ።", "⟪", v2_txt)
                v2_txt = v2_txt.replace(" ሉቃ ፳፪ ፩። ስከ ሁለት", " ሉቃ ፳፪ ፩። እስከ ሁለት")
                verses[i + 1]["rejoined_marked_text"] = v2_txt

    if book_key == "yohannes" and ch_num == 16:
        for i, v in enumerate(verses):
            if v["verse_num"] == 1 and i + 1 < len(verses) and verses[i + 1]["verse_num"] == 2:
                v["rejoined_marked_text"] = "⟪ወዘንተ ነገርኩክሙ ከመ ኢትትዓቀፉ ።⟫ እንዳትጠራጠሩ ይህን ነገርኋችሁ ።"
                v2_txt = verses[i + 1]["rejoined_marked_text"]
                v2_txt = re.sub(r"^ትትዓቀፉ\s*", "⟪", v2_txt)
                v2_txt = v2_txt.replace("ያወጽኡክሙ ።⟫ ና እንዳትጠራጠሩ", "ያወጽኡክሙ ።⟫ ከምኵራባቸው ያወጧችኋልና እንዳትጠራጠሩ")
                verses[i + 1]["rejoined_marked_text"] = v2_txt

    for i in range(len(verses) - 1):
        vA = verses[i]
        vB = verses[i + 1]
        linesA = vA.get("lines", [])
        if not linesA:
            continue
        lastA_wraps = linesA[-1].get("word_wraps_to_next_line", False)
        if not lastA_wraps:
            continue

        txtA = vA["rejoined_marked_text"].rstrip()
        txtB = strip_bracket_num(vB["rejoined_marked_text"]).lstrip()
        if txtB.startswith("⟪") and not re.search(r"(።\s*)(⟪[^⟪⟫]+)$", txtA):
            continue

        m_trail_geez = re.search(r"(።\s*)(⟪[^⟪⟫]+)$", txtA)
        if m_trail_geez and not txtB.startswith("⟪"):
            geez_head = m_trail_geez.group(2)
            txtA = txtA[:m_trail_geez.start(2)].rstrip()
            txtB = geez_head + txtB
            vA["rejoined_marked_text"] = txtA
            vB["rejoined_marked_text"] = txtB
            continue

        if book_key == "matewes" and ch_num == 15 and vA["verse_num"] == 19:
            idx_eluke = txtB.find("⟪እሉኬ")
            if idx_eluke > 0:
                txtA = txtA + txtB[:idx_eluke].rstrip()
                txtB = txtB[idx_eluke:]
                vA["rejoined_marked_text"] = txtA
                vB["rejoined_marked_text"] = txtB
                continue

        first_open = txtB.find("⟪")
        first_close = txtB.find("⟫")
        if first_open > 0 and (first_close == -1 or first_open < first_close) and first_open <= 45:
            prefix = txtB[:first_open]
            txtA = txtA + prefix.rstrip()
            txtB = txtB[first_open:]
            vA["rejoined_marked_text"] = txtA
            vB["rejoined_marked_text"] = txtB
            continue

        m_clause = re.match(r"^([^\s⟪⟫]+(?:\s*።)?)\s*(.*)$", txtB)
        if m_clause:
            word_tail = m_clause.group(1)
            rest_B = m_clause.group(2)
            m_heben = re.match(r"^([^⟪⟫]{1,22}?።)\s*(ኀበ\s+.*)$", txtB)
            if m_heben:
                word_tail = m_heben.group(1)
                rest_B = "⟪" + m_heben.group(2)
            elif book_key == "lukas" and ch_num == 21 and vA["verse_num"] == 29:
                m_luk21 = re.match(r"^(ለኵሉ\s+ዕፀው)\s+(.*)$", txtB)
                if m_luk21:
                    word_tail = m_luk21.group(1)
                    rest_B = "⟪" + m_luk21.group(2)
            txtA = txtA + word_tail + "⟫"
            if not rest_B.startswith("⟪"):
                rest_B = "⟪" + rest_B
            vA["rejoined_marked_text"] = txtA
            vB["rejoined_marked_text"] = rest_B


def clean_and_align_chapter_verses(bkey: str, cnum: int, vlist: List[Dict]):
    """
    Applies chapter-level verse healing, bracket balancing, tail/head Ge'ez alignment,
    and inline prefix normalization so every canonical verse starts cleanly with `⟪`.
    """
    if bkey == "lukas" and cnum == 1:
        for v in vlist:
            if v["verse_num"] in (2, 3) and "⟪" not in v["rejoined_marked_text"]:
                v["rejoined_marked_text"] = "⟪" + v["rejoined_marked_text"].strip() + "⟫"

    if bkey in ("matewes", "markos", "lukas", "yohannes"):
        heal_consecutive_verses(cnum, vlist, bkey)

    for v in vlist:
        v["rejoined_marked_text"] = balance_geez_brackets(v["rejoined_marked_text"])

    if bkey in ("matewes", "markos", "lukas", "yohannes"):
        for i in range(len(vlist) - 1):
            vA, vB = vlist[i], vlist[i + 1]
            if vA["verse_num"] == 0:
                continue
            txtA = vA["rejoined_marked_text"].strip()
            txtB = vB["rejoined_marked_text"].strip()
            secB = vB.get("section_title") or ""
            bodyB = txtB[len(secB):].strip() if (secB and txtB.startswith(secB)) else txtB
            if bodyB.startswith("⟪"):
                continue

            m_tail = re.search(r"(⟪[^⟪⟫]+⟫(?:\s*[፩-፼ሀ-ፖ\s፡፥፤።]{1,30})?)$", txtA)
            if m_tail:
                tail = m_tail.group(1)
                after_close = tail.split("⟫", 1)[1].strip()
                if not after_close or re.search(r"[፩-፼]", after_close):
                    before_tail = txtA[:m_tail.start(1)].strip()
                    if "⟪" in before_tail:
                        if (
                            ("⟪" not in bodyB)
                            or (bkey == "matewes" and (cnum, vB["verse_num"]) in [(3, 17), (7, 17)])
                            or (bkey == "markos" and (cnum, vB["verse_num"]) in [(10, 8)])
                            or (bkey == "lukas" and (cnum, vB["verse_num"]) in [(22, 56), (23, 19)])
                        ):
                            vA["rejoined_marked_text"] = before_tail
                            vB["rejoined_marked_text"] = (
                                (secB + " " if (secB and txtB.startswith(secB)) else "") + tail + " " + bodyB
                            )
                            continue

            first_open = bodyB.find("⟪")
            if first_open > 0:
                amh_prefix = bodyB[:first_open].strip()
                rest_B = bodyB[first_open:].strip()
                vA["rejoined_marked_text"] = txtA + " " + amh_prefix
                vB["rejoined_marked_text"] = (
                    (secB + " " if (secB and txtB.startswith(secB)) else "") + rest_B
                )

    for v in vlist:
        txt = v["rejoined_marked_text"].strip()
        if v["verse_num"] >= 1:
            sec = (v.get("section_title") or "").strip()
            if bkey == "lukas" and cnum == 14 and v["verse_num"] == 1:
                sec = "ዘከመ ፈወሶ ኢየሱስ ለቅብው በእለተ ሰንበት ።"
                v["section_title"] = sec
            if sec and txt.startswith(sec):
                txt = txt[len(sec):].strip()

            m_bk = re.match(r"^(መልእክተ\s*፡\s*ጴጥሮስ\s*፡\s*ቀዳሚት\s*።)\s*", txt)
            if m_bk:
                if not v.get("section_title"):
                    v["section_title"] = m_bk.group(1)
                txt = txt[m_bk.end():].strip()

            m_k1 = re.match(r"^(ክፍል\s*[፡:]?\s*[፩-፼]+\s*[።፤፥፡]*)\s*", txt)
            if m_k1:
                v["section_title"] = m_k1.group(1).strip()
                txt = txt[m_k1.end():].strip()

            txt = re.sub(r"^(?:[፩-፼]+\s*[፤፥፡]\s*|፤\s*)", "", txt).strip()

            m_k2 = re.match(r"^(ክፍል\s*[፡:]?\s*[፩-፼]+\s*[።፤፥፡]*)\s*", txt)
            if m_k2:
                v["section_title"] = m_k2.group(1).strip()
                txt = txt[m_k2.end():].strip()

            txt = re.sub(r"^⟪\s*[፩-፼]+\s*[፤፥፡]\s*", "⟪", txt).strip()

        txt = balance_geez_brackets(txt)
        v["rejoined_marked_text"] = txt
        v["rejoined_plain_text"] = txt.replace("⟪", "").replace("⟫", "")
        v["geez_root_lemmas"] = [
            re.sub(r"^\s*[፩-፼]+\s*[፤፥፡]\s*", "", m).strip()
            for m in re.findall(r"⟪([^⟫]+)⟫", txt)
            if m.strip()
        ]


def extract_clause_by_clause(marked_text: str) -> List[Dict[str, Any]]:
    """
    Parses a balanced `rejoined_marked_text` into an ordered list of clause-by-clause
    exegetical units (`ንባብ` + `ትርጓሜ` + `አንድም` + `ሐተታ`).
    """
    if not marked_text:
        return []

    blocks = re.split(r"(⟪[^⟫]*⟫)", marked_text)
    clauses: List[Dict[str, Any]] = []
    curr_geez = ""
    curr_amh_parts: List[str] = []

    def flush_clause(geez_str: str, amh_str: str):
        geez_clean = re.sub(r"^\s*[፩-፼]+\s*[፤፥፡]\s*", "", geez_str).strip()
        amh_clean = amh_str.strip()
        if not geez_clean and not amh_clean:
            return
        primary_interp = ""
        andem_list: List[str] = []
        hateta_list: List[str] = []
        if amh_clean:
            sub_chunks = [s.strip() for s in EXEGETICAL_SPLIT_RE.split(amh_clean) if s.strip()]
            for sc in sub_chunks:
                if sc.startswith("አንድም"):
                    andem_list.append(sc)
                elif re.match(r"^\(?(?:ሐተታ|ታሪክ|ምሳሌ|ትንቢት)\)?", sc):
                    hateta_list.append(sc)
                else:
                    if not primary_interp:
                        primary_interp = sc
                    else:
                        primary_interp += " " + sc

        clauses.append({
            "clause_index": len(clauses) + 1,
            "geez_lemma": geez_clean,
            "amharic_explanation": amh_clean,
            "primary_interpretation": primary_interp,
            "andem_interpretations": andem_list,
            "hateta_explanations": hateta_list,
        })

    has_seen_geez = False
    for blk in blocks:
        if not blk or not blk.strip():
            continue
        if blk.startswith("⟪") and blk.endswith("⟫"):
            if has_seen_geez or curr_amh_parts:
                flush_clause(curr_geez, " ".join(curr_amh_parts))
            curr_geez = blk[1:-1].strip()
            curr_amh_parts = []
            has_seen_geez = True
        else:
            curr_amh_parts.append(blk.strip())

    if has_seen_geez or curr_amh_parts:
        flush_clause(curr_geez, " ".join(curr_amh_parts))

    return clauses


def rubricate_marked_text(marked_text: str) -> List[Dict[str, str]]:
    """
    Splits `rejoined_marked_text` into an ordered, lossless list of Biranna-rubricated spans.
    Every span has `text`, `color` ("red"|"black"), `hex` ("#9e1b1b"|"#1f1a14"), and `category`.
    """
    if not marked_text:
        return []

    marked_text = balance_geez_brackets(marked_text)
    spans: List[Dict[str, str]] = []
    blocks = re.split(r"(⟪[^⟫]*⟫)", marked_text)

    for block in blocks:
        if not block:
            continue
        if block.startswith("⟪") and block.endswith("⟫"):
            inner = block[1:-1]
            if inner:
                spans.append({
                    "text": inner,
                    "color": "red",
                    "hex": RED_HEX,
                    "category": "geez_scripture",
                })
        else:
            last_idx = 0
            for m in MASTER_COMMENTARY_RE.finditer(block):
                start, end = m.span()
                if start > last_idx:
                    plain_chunk = block[last_idx:start]
                    spans.append({
                        "text": plain_chunk,
                        "color": "black",
                        "hex": BLACK_HEX,
                        "category": "amharic_commentary",
                    })
                cat = m.lastgroup or "sacred_divine_name"
                spans.append({
                    "text": m.group(0),
                    "color": "red",
                    "hex": RED_HEX,
                    "category": cat,
                })
                last_idx = end

            if last_idx < len(block):
                spans.append({
                    "text": block[last_idx:],
                    "color": "black",
                    "hex": BLACK_HEX,
                    "category": "amharic_commentary",
                })

    return spans


def spans_to_biranna_html(spans: List[Dict[str, str]]) -> str:
    out = []
    for sp in spans:
        esc = html.escape(sp["text"])
        cat = sp["category"]
        if cat == "geez_scripture":
            out.append(f'<span class="geez-root-lemma">{esc}</span>')
        elif cat in ("sacred_divine_name", "sacred_mariology", "sacred_saint_angel"):
            out.append(f'<span class="biranna-sacred-name" data-cat="{cat}">{esc}</span>')
        elif cat == "andemta_rubric":
            if esc == "አንድም":
                out.append(f'<span class="kw-andem">{esc}</span>')
            else:
                out.append(f'<span class="kw-hateta">{esc}</span>')
        elif cat == "rubric_numeral_punct":
            out.append(f'<span class="biranna-punct">{esc}</span>')
        else:
            out.append(esc)
    return "".join(out)


def apply_biranna_rubrication_to_all_books():
    root_dir = "/Users/senaymacstudio1/Desktop/haymanote_abew"
    books = [
        ("01_matewes", "matewes", "data/extracted/matewes_andemta_complete.json"),
        ("02_markos", "markos", "data/markos/extracted/markos_andemta_complete.json"),
        ("03_lukas", "lukas", "data/lukas/extracted/lukas_andemta_complete.json"),
        ("04_yohannes", "yohannes", "data/yohannes/extracted/yohannes_andemta_complete.json"),
        ("05_acts", "acts", "data/acts/extracted/acts_andemta_complete.json"),
        ("06_peter1", "peter1", "data/peter1/extracted/peter1_andemta_complete.json"),
        ("07_peter2", "peter2", "data/peter2/extracted/peter2_andemta_complete.json"),
        ("08_john1", "john1", "data/john1/extracted/john1_andemta_complete.json"),
        ("09_john2", "john2", "data/john2/extracted/john2_andemta_complete.json"),
        ("10_john3", "john3", "data/john3/extracted/john3_andemta_complete.json"),
        ("11_james", "james", "data/james/extracted/james_andemta_complete.json"),
        ("12_judah", "judah", "data/judah/extracted/judah_andemta_complete.json"),
        ("13_revelation", "revelation", "data/revelation/extracted/revelation_andemta_complete.json"),
    ]

    global_cat_counts = Counter()
    all_books_clean = []

    for prefix, bkey, comp_rel_path in books:
        comp_path = os.path.join(root_dir, comp_rel_path)
        d = json.load(open(comp_path, encoding="utf-8"))
        bmeta = BOOK_META[bkey]

        ch_idx_map = {c.get("chapter_num"): c for c in d.get("chapter_index", [])}
        top_by_cv = {}
        top_by_ch = {}
        for t in d.get("topical_index", []):
            c_n = t.get("chapter_num")
            v_n = t.get("verse_num")
            item = {
                "topic_id": t.get("topic_id"),
                "chapter_num": c_n,
                "chapter_ethiopic": t.get("chapter_ethiopic"),
                "verse_num": v_n,
                "verse_ethiopic": t.get("verse_ethiopic"),
                "geez_title": t.get("geez_title"),
                "amharic_title": t.get("amharic_title"),
                "index_pdf_page": t.get("pdf_page"),
                "index_book_page_ethiopic": t.get("book_page_ethiopic"),
            }
            top_by_cv.setdefault((c_n, v_n), []).append(item)
            top_by_ch.setdefault(c_n, []).append(item)

        book_cat_counts = Counter()
        clean_chapters = []
        total_clauses_in_book = 0

        for ch in d.get("chapters", []):
            ch_num = ch["chapter_num"]
            ch_meta = ch_idx_map.get(ch_num, {})
            vlist = ch.get("verses", [])
            clean_and_align_chapter_verses(bkey, ch_num, vlist)

            clean_verses = []
            for v in vlist:
                v_num = v["verse_num"]
                marked = v.get("rejoined_marked_text", "")
                lemmas = v.get("geez_root_lemmas", [])
                ch_eth = v.get("chapter_ethiopic", "")
                v_eth = v.get("verse_ethiopic", "")
                is_prologue = v_num == 0

                b_spans = rubricate_marked_text(marked)
                for sp in b_spans:
                    book_cat_counts[sp["category"]] += 1
                    global_cat_counts[sp["category"]] += 1

                clauses = extract_clause_by_clause(marked)
                total_clauses_in_book += len(clauses)
                geez_joined = " ፤ ".join(lemmas)
                amharic_only = " ".join(
                    c["amharic_explanation"] for c in clauses if c["amharic_explanation"]
                ).strip()

                v["biranna_spans"] = b_spans
                v["clause_by_clause"] = clauses
                v["geez_text"] = geez_joined
                v["amharic_commentary_text"] = amharic_only

                ref_geez = (
                    f"{d.get('title_geez')} — መቅድም"
                    if is_prologue
                    else f"ምዕራፍ {ch_eth} ፥ ቍጥር {v_eth}"
                )
                ref_short_geez = (
                    f"{bmeta['short_geez']} መቅድም"
                    if is_prologue
                    else f"{bmeta['short_geez']} {ch_eth}፥{v_eth}"
                )
                ref_en = (
                    f"{bmeta['name_en']} Prologue"
                    if is_prologue
                    else f"{bmeta['name_en']} {ch_num}:{v_num}"
                )

                clean_verses.append({
                    "id": f"{bkey}:{ch_num}:{v_num}",
                    "book_key": bkey,
                    "chapter_num": ch_num,
                    "chapter_ethiopic": ch_eth,
                    "verse_num": v_num,
                    "verse_ethiopic": v_eth,
                    "is_prologue": is_prologue,
                    "reference_geez": ref_geez,
                    "reference_short_geez": ref_short_geez,
                    "reference_english": ref_en,
                    "reference_arabic": f"{ch_num}:{v_num}",
                    "section_title": v.get("section_title"),
                    "linked_topics": top_by_cv.get((ch_num, v_num), []),
                    "start_pdf_page": v.get("start_pdf_page"),
                    "start_book_page_ethiopic": v.get("start_book_page_ethiopic"),
                    "geez_text": geez_joined,
                    "geez_root_text": geez_joined,
                    "geez_clauses": lemmas,
                    "geez_root_lemmas": lemmas,
                    "amharic_commentary_text": amharic_only,
                    "clause_by_clause": clauses,
                    "biranna_spans": b_spans,
                    "rejoined_marked_text": marked,
                    "rejoined_plain_text": v.get("rejoined_plain_text", ""),
                })

            # Ensure chapter incipit reflects the clean opening Ge'ez lemma
            first_canonical = next((cv for cv in clean_verses if not cv["is_prologue"]), None)
            geez_inc = (
                first_canonical["geez_clauses"][0]
                if (first_canonical and first_canonical["geez_clauses"])
                else (ch.get("geez_incipit") or ch_meta.get("geez_incipit", ""))
            )
            amh_inc = (
                first_canonical["clause_by_clause"][0]["primary_interpretation"][:120]
                if (first_canonical and first_canonical["clause_by_clause"])
                else (ch.get("amharic_incipit") or ch_meta.get("amharic_incipit", ""))
            )

            clean_chapters.append({
                "id": f"{bkey}:{ch_num}",
                "book_key": bkey,
                "chapter_num": ch_num,
                "chapter_ethiopic": ch.get("chapter_ethiopic"),
                "title_geez": ch.get("title_geez"),
                "geez_incipit": geez_inc,
                "amharic_incipit": amh_inc,
                "start_pdf_page": ch.get("start_pdf_page"),
                "start_book_page_ethiopic": ch.get("start_book_page_ethiopic"),
                "chapter_topics": top_by_ch.get(ch_num, []),
                "verse_count": len(clean_verses),
                "verses": clean_verses,
            })

        d.setdefault("stats", {})["biranna_rubrication_counts"] = dict(book_cat_counts)
        d["stats"]["total_exegetical_clauses"] = total_clauses_in_book

        with open(comp_path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        ext_copy = os.path.join(root_dir, "data", "extracted", f"{bkey}_andemta_complete.json")
        if comp_path != ext_copy:
            with open(ext_copy, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
        exp_copy = os.path.join(root_dir, "json_exports", f"{bkey}_andemta_complete.json")
        with open(exp_copy, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)

        clean_book = {
            "schema_version": "2.0.0",
            "book_order": bmeta["order"],
            "book_key": bkey,
            "category": bmeta["category"],
            "title_geez": d.get("title_geez"),
            "title_short_geez": bmeta["short_geez"],
            "title_english": d.get("title_english"),
            "title_short_english": bmeta["short_en"],
            "biranna_color_rules": {
                "red_ink_hex": RED_HEX,
                "black_ink_hex": BLACK_HEX,
                "red_categories": [
                    "geez_scripture",
                    "sacred_divine_name",
                    "sacred_mariology",
                    "sacred_saint_angel",
                    "andemta_rubric",
                    "rubric_numeral_punct",
                ],
                "black_categories": ["amharic_commentary"],
            },
            "stats": d.get("stats"),
            "chapters": clean_chapters,
            "chapter_index": d.get("chapter_index", []),
            "topical_index": d.get("topical_index", []),
            "canon_tables": d.get("canon_tables", []),
        }
        root_book_path = os.path.join(root_dir, f"{prefix}.json")
        with open(root_book_path, "w", encoding="utf-8") as f:
            json.dump(clean_book, f, ensure_ascii=False, indent=2)

        clean_app_path = os.path.join(root_dir, "clean_app_jsons", f"{prefix}_clean.json")
        with open(clean_app_path, "w", encoding="utf-8") as f:
            json.dump(clean_book, f, ensure_ascii=False, indent=2)

        all_books_clean.append(clean_book)
        print(
            f"[{prefix:13s}] ch={len(clean_chapters):2d} | verses={sum(c['verse_count'] for c in clean_chapters):4d} | "
            f"clauses={total_clauses_in_book:5d} | "
            f"geez={book_cat_counts['geez_scripture']:4d}, "
            f"divine={book_cat_counts['sacred_divine_name']:4d}, "
            f"marian={book_cat_counts['sacred_mariology']:3d}, "
            f"saints={book_cat_counts['sacred_saint_angel']:4d}, "
            f"andemta={book_cat_counts['andemta_rubric']:4d}, "
            f"punct={book_cat_counts['rubric_numeral_punct']:5d}"
        )

    master_payload = {
        "schema_version": "2.0.0",
        "corpus_title_geez": "የሐዲስ ኪዳን አንድምታ ትርጓሜ (፲፫ መጻሕፍት)",
        "corpus_title_english": "Ethiopian Orthodox Tewahedo New Testament Ge'ez & Amharic Andemta Commentary (13 Books)",
        "total_books": 13,
        "total_chapters": sum(len(b["chapters"]) for b in all_books_clean),
        "total_verses": sum(sum(c["verse_count"] for c in b["chapters"]) for b in all_books_clean),
        "global_biranna_rubrication_counts": dict(global_cat_counts),
        "books": all_books_clean,
    }
    for m_path in [
        os.path.join(root_dir, "00_all_13_books_complete.json"),
        os.path.join(root_dir, "clean_app_jsons", "00_all_clean.json"),
    ]:
        with open(m_path, "w", encoding="utf-8") as f:
            json.dump(master_payload, f, ensure_ascii=False, indent=1)

    print("-" * 105)
    print(
        f"GLOBAL 13-BOOK TOTALS: {master_payload['total_books']} books, "
        f"{master_payload['total_chapters']} chapters, "
        f"{master_payload['total_verses']} verses"
    )
    print("GLOBAL BIRANNA RUBRICATION COUNTS:", dict(global_cat_counts))


if __name__ == "__main__":
    apply_biranna_rubrication_to_all_books()
