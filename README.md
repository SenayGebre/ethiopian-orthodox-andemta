# የሐዲስ ኪዳን አንድምታ ትርጓሜ (፲፫ መጻሕፍት)
## Ethiopian Orthodox Tewahedo New Testament Ge'ez & Amharic *Andemta* Commentary — Open-Source Corpus (`v2.0.0`)

A 100% complete, philologically verified, open-source JSON edition of the **13 New Testament Ge'ez (`ልሳነ ግዕዝ`) and Amharic (`አማርኛ`) *Andemta* Commentary books** of the Ethiopian Orthodox Tewahedo Church, featuring authentic **Ethiopian *Biranna* (`ብራና`) red-and-black manuscript rubrication** (`የቀይና ጥቁር ቀለም ሥርዓት`) and **clause-by-clause exegetical pairing** (`ንባብና ትርጓሜ`).

---

## 1. Corpus Summary (13 Books · 160 Chapters · 5,614 Verses · 14,584 Exegetical Clauses)

| # | Universal Book JSON (Root) | Full Diplomatic Edition (Line-by-Line) | Book Key | Ge'ez Title | English Title | PDF Pages | Chapters | Verses | Exegetical Clauses | Diplomatic Lines |
| :-: | :--- | :--- | :--- | :--- | :--- | :-: | :-: | :-: | :-: | :-: |
| **All** | [`00_all_13_books_complete.json`](./00_all_13_books_complete.json) | [`data/extracted/`](./data/extracted/) | `all` | የሐዲስ ኪዳን አንድምታ ትርጓሜ (፲፫ መጻሕፍት) | Complete 13-Book Corpus | **771** | **160** | **5,614** | **14,584** | **89,557** |
| **01** | [`01_matewes.json`](./01_matewes.json) | [`matewes_andemta_complete.json`](./data/extracted/matewes_andemta_complete.json) | `matewes` | የማቴዎስ ወንጌል አንድምታ | Gospel of Matthew | 212 | 28 | 1,070 | 2,677 | 23,604 |
| **02** | [`02_markos.json`](./02_markos.json) | [`markos_andemta_complete.json`](./data/extracted/markos_andemta_complete.json) | `markos` | የማርቆስ ወንጌል አንድምታ | Gospel of Mark | 67 | 16 | 678 | 1,515 | 7,498 |
| **03** | [`03_lukas.json`](./03_lukas.json) | [`lukas_andemta_complete.json`](./data/extracted/lukas_andemta_complete.json) | `lukas` | የሉቃስ ወንጌል አንድምታ | Gospel of Luke | 131 | 24 | 1,146 | 3,028 | 14,768 |
| **04** | [`04_yohannes.json`](./04_yohannes.json) | [`yohannes_andemta_complete.json`](./data/extracted/yohannes_andemta_complete.json) | `yohannes` | የዮሐንስ ወንጌል አንድምታ | Gospel of John | 116 | 21 | 872 | 2,269 | 12,751 |
| **05** | [`05_acts.json`](./05_acts.json) | [`acts_andemta_complete.json`](./data/extracted/acts_andemta_complete.json) | `acts` | የሐዋርያት ሥራ አንድምታ | Acts of the Apostles | 91 | 28 | 1,004 | 2,538 | 12,008 |
| **06** | [`06_peter1.json`](./06_peter1.json) | [`peter1_andemta_complete.json`](./data/extracted/peter1_andemta_complete.json) | `peter1` | የጴጥሮስ መልእክት ቀዳማዊ አንድምታ | 1 Peter | 31 | 5 | 106 | 330 | 3,871 |
| **07** | [`07_peter2.json`](./07_peter2.json) | [`peter2_andemta_complete.json`](./data/extracted/peter2_andemta_complete.json) | `peter2` | የጴጥሮስ መልእክት ካልዕ አንድምታ | 2 Peter | 13 | 3 | 61 | 188 | 1,598 |
| **08** | [`08_john1.json`](./08_john1.json) | [`john1_andemta_complete.json`](./data/extracted/john1_andemta_complete.json) | `john1` | የዮሐንስ መልእክት ቀዳማዊ አንድምታ | 1 John | 15 | 5 | 105 | 308 | 1,822 |
| **09** | [`09_john2.json`](./09_john2.json) | [`john2_andemta_complete.json`](./data/extracted/john2_andemta_complete.json) | `john2` | የዮሐንስ መልእክት ካልዕ አንድምታ | 2 John | 3 | 1 | 14 | 41 | 236 |
| **10** | [`10_john3.json`](./10_john3.json) | [`john3_andemta_complete.json`](./data/extracted/john3_andemta_complete.json) | `john3` | የዮሐንስ መልእክት ሣልስ አንድምታ | 3 John | 3 | 1 | 16 | 39 | 224 |
| **11** | [`11_james.json`](./11_james.json) | [`james_andemta_complete.json`](./data/extracted/james_andemta_complete.json) | `james` | የያዕቆብ መልእክት አንድምታ | Epistle of James | 14 | 5 | 109 | 290 | 1,848 |
| **12** | [`12_judah.json`](./12_judah.json) | [`judah_andemta_complete.json`](./data/extracted/judah_andemta_complete.json) | `judah` | የይሁዳ መልእክት አንድምታ | Epistle of Jude | 4 | 1 | 26 | 92 | 456 |
| **13** | [`13_revelation.json`](./13_revelation.json) | [`revelation_andemta_complete.json`](./data/extracted/revelation_andemta_complete.json) | `revelation` | የዮሐንስ ራእይ አንድምታ | Book of Revelation | 71 | 22 | 407 | 1,269 | 8,873 |

> **Full Diplomatic Editions** (including raw page-by-page, column-by-column, line-by-line coordinates and Stage-2 Yeneta Fidel correction logs) are available in [`data/extracted/`](./data/extracted/).

---

## 2. Universal Open-Source JSON Schema (`v2.0.0`)

Formal JSON Schema definition: [`schema.json`](./schema.json).

Every verse object across all 13 books provides **three complementary representations** so you can build any application without writing custom regexes or parsers:

1. **Direct Text & Lemma Fields**:
   - `id`: Globally unique verse identifier (e.g., `"matewes:1:1"`, `"acts:2:1"`).
   - `geez_text`: Pure Ge'ez root scripture (`ንባብ`) of the verse.
   - `geez_clauses`: Array of individual Ge'ez scripture clauses in the verse.
   - `amharic_commentary_text`: Pure Amharic commentary (`ትርጓሜ`) of the verse.
   - `rejoined_marked_text`: Full text with `⟪...⟫` wrapping Ge'ez scripture.
   - `rejoined_plain_text`: Full plain text without `⟪...⟫`.
2. **Structured Clause-by-Clause Exegesis (`clause_by_clause`)**:
   - Pairs each Ge'ez clause (`geez_lemma`) with its immediate Amharic commentary (`amharic_explanation`), split into:
     - `primary_interpretation`: Initial direct translation/explanation.
     - `andem_interpretations`: Array of `አንድም` alternative exegetical interpretations.
     - `hateta_explanations`: Array of `ሐተታ` / `ታሪክ` / `ምሳሌ` / `ትንቢት` deep theological and historical notes.
3. **Lossless Biranna Manuscript Spans (`biranna_spans`)**:
   - Pre-tokenized array of `{ "text", "color", "hex", "category" }` spans where concatenating `span.text` reconstructs `rejoined_plain_text` with **zero characters lost**.

### Sample Verse Object (`01_matewes.json`, Matthew 1:1)
```json
{
  "id": "matewes:1:1",
  "book_key": "matewes",
  "chapter_num": 1,
  "chapter_ethiopic": "፩",
  "verse_num": 1,
  "verse_ethiopic": "፩",
  "is_prologue": false,
  "reference_geez": "ምዕራፍ ፩ ፥ ቍጥር ፩",
  "reference_short_geez": "ማቴ ፩፥፩",
  "reference_english": "Matthew 1:1",
  "reference_arabic": "1:1",
  "section_title": "ወንጌል ቅዱስ ዘሰበከ ማቴዎስ ።",
  "linked_topics": [],
  "start_pdf_page": 22,
  "start_book_page_ethiopic": "፳፪",
  "geez_text": "መጽሐፈ ልደቱ ለእግዚእነ ኢየሱስ ክርስቶስ ። ፤ ወልደ ዳዊት ወልደ አብርሃም",
  "geez_clauses": [
    "መጽሐፈ ልደቱ ለእግዚእነ ኢየሱስ ክርስቶስ ።",
    "ወልደ ዳዊት ወልደ አብርሃም"
  ],
  "amharic_commentary_text": "ወንጌላውያን ሲጽፉ ራሳቸውን መሠረት አያደርጉም ...",
  "clause_by_clause": [
    {
      "clause_index": 1,
      "geez_lemma": "መጽሐፈ ልደቱ ለእግዚእነ ኢየሱስ ክርስቶስ ።",
      "amharic_explanation": "ወንጌላውያን ሲጽፉ ...",
      "primary_interpretation": "ወንጌላውያን ሲጽፉ ...",
      "andem_interpretations": ["አንድም ልደቱ ዘእምአብ የማይመረመር ..."],
      "hateta_explanations": ["ሐተታ ፡ ወንጌላውያን ወንጌልን መጻف ስለ ምን ነው ቢሉ ..."]
    }
  ],
  "biranna_spans": [
    {
      "text": "መጽሐፈ ልደቱ ለእግዚእነ ኢየሱስ ክርስቶስ ።",
      "color": "red",
      "hex": "#9e1b1b",
      "category": "geez_scripture"
    },
    {
      "text": " ወንጌላውያን ሲጽፉ ራሳቸውን መሠረት አያደርጉም ...",
      "color": "black",
      "hex": "#1f1a14",
      "category": "amharic_commentary"
    }
  ]
}
```

---

## 3. Authentic Ethiopian *Biranna* (`ብራና`) Manuscript Color Rules (`ቀይና ጥቁር ቀለም`)

In the Ethiopian Orthodox Tewahedo scribal tradition (*Куmczek / ብራና ጽሕፈት*), manuscripts are written with two sacred inks: **Cinnabar/Ochre Red (`ቀይ ቀለም`, `#9e1b1b`)** and **Carbon Black (`ጥቁር ቀለም`, `#1f1a14`)**.

| Category Key | Ink Color | Hex | Traditional Role (`ሥርዓተ ብራና`) | Corpus Count |
| :--- | :---: | :---: | :--- | ---: |
| `geez_scripture` | **Red** (`ቀይ`) | `#9e1b1b` | Root Ge'ez biblical text (`ንባብ`) enclosed in `⟪...⟫` | 14,575 |
| `sacred_divine_name` | **Red** (`ቀይ`) | `#9e1b1b` | Names of the Holy Trinity & God (`እግዚአብሔር`, `ኢየሱስ ክርስቶስ`, `መንፈስ ቅዱስ`, `ሥላሴ`, `አማኑኤል`, `መድኃኔ ዓለም`, `ጰራቅሊጦስ`, `ጌታችን`, etc.) | 3,714 |
| `sacred_mariology` | **Red** (`ቀይ`) | `#9e1b1b` | Names & titles of St. Mary (`እመቤታችን`, `ቅድስት ድንግል ማርያም`, `ወላዲተ አምላክ`, `እግዝእትነ`) | 155 |
| `sacred_saint_angel` | **Red** (`ቀይ`) | `#9e1b1b` | Archangels, Apostles, Evangelists, Prophets & Church Fathers (`ቅዱሳን፣ መላእክት፣ ነቢያት፣ ሐዋርያት፣ ሊቃውንት`) | 2,941 |
| `andemta_rubric` | **Red** (`ቀይ`) | `#9e1b1b` | Exegetical structural dividers (`አንድም`, `ሐተታ`, `ታሪክ`, `ምሳሌ`, `ትንቢት`, `ጥቅስ`) | 3,989 |
| `rubric_numeral_punct` | **Red** (`ቀይ`) | `#9e1b1b` | Ethiopic numerals (`፩`–`፼`) and four-dot full stops (`።`, `፠`) | 25,661 |
| `amharic_commentary` | **Black** (`ጥቁር`) | `#1f1a14` | Primary Amharic *Andemta* commentary (`ትርጓሜ`) | 45,466 |

---

## 4. Quick Integration Examples Across Any Technology Stack

### React / Next.js (TypeScript)
```tsx
import React from 'react';

interface BirannaSpan {
  text: string;
  color: 'red' | 'black';
  hex: string;
  category: string;
}

export function AndemtaVerse({ verse }: { verse: { reference_short_geez: string; biranna_spans: BirannaSpan[] } }) {
  return (
    <p style={{ fontFamily: "'Noto Serif Ethiopic', serif", lineHeight: 2.0, fontSize: '1.15rem' }}>
      <strong>[{verse.reference_short_geez}] </strong>
      {verse.biranna_spans.map((span, idx) => (
        <span
          key={idx}
          style={{
            color: span.hex,
            fontWeight: span.category === 'geez_scripture' || span.color === 'red' ? 600 : 400,
          }}
        >
          {span.text}
        </span>
      ))}
    </p>
  );
}
```

### Flutter / Dart
```dart
import 'package:flutter/material.dart';

Widget buildBirannaVerse(Map<String, dynamic> verse) {
  final spans = (verse['biranna_spans'] as List).cast<Map<String, dynamic>>();
  return RichText(
    text: TextSpan(
      style: const TextStyle(
        fontFamily: 'NotoSerifEthiopic',
        fontSize: 18,
        height: 1.9,
      ),
      children: spans.map((sp) {
        final isRed = sp['color'] == 'red';
        return TextSpan(
          text: sp['text'] as String,
          style: TextStyle(
            color: isRed ? const Color(0xFF9E1B1B) : const Color(0xFF1F1A14),
            fontWeight: sp['category'] == 'geez_scripture' ? FontWeight.w700 : FontWeight.w400,
          ),
        );
      }).toList(),
    ),
  );
}
```

### iOS / SwiftUI
```swift
import SwiftUI

struct BirannaSpan: Decodable {
    let text: String
    let color: String
    let hex: String
    let category: String
}

func renderBirannaText(spans: [BirannaSpan]) -> Text {
    spans.reduce(Text("")) { acc, span in
        let inkColor = span.color == "red"
            ? Color(red: 0.62, green: 0.106, blue: 0.106)
            : Color(red: 0.122, green: 0.102, blue: 0.078)
        return acc + Text(span.text)
            .foregroundColor(inkColor)
            .fontWeight(span.category == "geez_scripture" ? .bold : .regular)
    }
}
```

### Python / NLP / RAG / AI Indexing
```python
import json

with open("01_matewes.json", encoding="utf-8") as f:
    book = json.load(f)

for chapter in book["chapters"]:
    for verse in chapter["verses"]:
        for clause in verse["clause_by_clause"]:
            print(f"[{verse['id']}#{clause['clause_index']}]")
            print("  ንባብ (Ge'ez):", clause["geez_lemma"])
            print("  ትርጓሜ (Primary):", clause["primary_interpretation"])
            for andem in clause["andem_interpretations"]:
                print("  አንድም (Alt):", andem)
```

---

## 5. Local Interactive Web Reader & Verification Server

Run the built-in 13-book interactive reader and REST API server:
```bash
./.venv/bin/python server.py
```
Then open **`http://localhost:8080`** in your browser.
