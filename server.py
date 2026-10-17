import glob
import json
import os
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import compile_book
import process_gospel_books
import process_dynamic_books

PORT = int(os.environ.get("PORT", "8080"))

BOOK_PATHS = {
    "matewes": {
        "raw_images": "data/raw_images",
        "pages_dir": "data/extracted/pages",
        "master_json": "data/extracted/matewes_andemta_complete.json",
    },
    "markos": {
        "raw_images": "data/markos/raw_images",
        "pages_dir": "data/markos/extracted/pages",
        "master_json": "data/markos/extracted/markos_andemta_complete.json",
    },
    "lukas": {
        "raw_images": "data/lukas/raw_images",
        "pages_dir": "data/lukas/extracted/pages",
        "master_json": "data/lukas/extracted/lukas_andemta_complete.json",
    },
    "yohannes": {
        "raw_images": "data/yohannes/raw_images",
        "pages_dir": "data/yohannes/extracted/pages",
        "master_json": "data/yohannes/extracted/yohannes_andemta_complete.json",
    },
    "acts": {
        "raw_images": "data/acts/raw_images",
        "pages_dir": "data/acts/extracted/pages",
        "master_json": "data/acts/extracted/acts_andemta_complete.json",
    },
    "peter1": {
        "raw_images": "data/peter1/raw_images",
        "pages_dir": "data/peter1/extracted/pages",
        "master_json": "data/peter1/extracted/peter1_andemta_complete.json",
    },
    "peter2": {
        "raw_images": "data/peter2/raw_images",
        "pages_dir": "data/peter2/extracted/pages",
        "master_json": "data/peter2/extracted/peter2_andemta_complete.json",
    },
    "john1": {
        "raw_images": "data/john1/raw_images",
        "pages_dir": "data/john1/extracted/pages",
        "master_json": "data/john1/extracted/john1_andemta_complete.json",
    },
    "john2": {
        "raw_images": "data/john2/raw_images",
        "pages_dir": "data/john2/extracted/pages",
        "master_json": "data/john2/extracted/john2_andemta_complete.json",
    },
    "john3": {
        "raw_images": "data/john3/raw_images",
        "pages_dir": "data/john3/extracted/pages",
        "master_json": "data/john3/extracted/john3_andemta_complete.json",
    },
    "james": {
        "raw_images": "data/james/raw_images",
        "pages_dir": "data/james/extracted/pages",
        "master_json": "data/james/extracted/james_andemta_complete.json",
    },
    "judah": {
        "raw_images": "data/judah/raw_images",
        "pages_dir": "data/judah/extracted/pages",
        "master_json": "data/judah/extracted/judah_andemta_complete.json",
    },
    "revelation": {
        "raw_images": "data/revelation/raw_images",
        "pages_dir": "data/revelation/extracted/pages",
        "master_json": "data/revelation/extracted/revelation_andemta_complete.json",
    },
}

_last_compiled_counts = {
    k: len(glob.glob(os.path.join(v["pages_dir"], "page_*.json")))
    for k, v in BOOK_PATHS.items()
    if os.path.exists(v["master_json"])
}


def get_book_cfg(book_key: str) -> dict:
    if book_key in process_gospel_books.BOOK_CONFIGS:
        return process_gospel_books.BOOK_CONFIGS[book_key]
    if book_key in process_dynamic_books.BOOKS_CONFIG:
        return process_dynamic_books.BOOKS_CONFIG[book_key]
    return {}


def recompile_book(book_key: str):
    import biranna_rubricator
    if book_key == "matewes":
        compile_book.compile_all()
    elif book_key in process_gospel_books.BOOK_CONFIGS:
        process_gospel_books.compile_book_data(process_gospel_books.BOOK_CONFIGS[book_key])
    elif book_key in process_dynamic_books.BOOKS_CONFIG:
        process_dynamic_books.compile_book_data(process_dynamic_books.BOOKS_CONFIG[book_key])
    biranna_rubricator.apply_biranna_rubrication_to_all_books()


def ensure_fresh_compilation(book_key: str = "matewes"):
    if book_key not in BOOK_PATHS:
        book_key = "matewes"
    binfo = BOOK_PATHS[book_key]
    curr_count = len(glob.glob(os.path.join(binfo["pages_dir"], "page_*.json")))
    if curr_count > 0 and (not os.path.exists(binfo["master_json"]) or curr_count != _last_compiled_counts.get(book_key, -1)):
        recompile_book(book_key)
        _last_compiled_counts[book_key] = curr_count


class AndemtaRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        book_key = (qs.get("book", ["matewes"])[0]).strip().lower()
        if book_key not in BOOK_PATHS:
            book_key = "matewes"
        binfo = BOOK_PATHS[book_key]

        if path == "/" or path == "/index.html":
            self.send_file("static/index.html", "text/html; charset=utf-8")
            return

        if path.startswith("/images/"):
            parts = [p for p in path.split("/") if p]
            if len(parts) == 3 and parts[1] in BOOK_PATHS:
                img_book = parts[1]
                fname = parts[2]
                fpath = os.path.join(BOOK_PATHS[img_book]["raw_images"], fname)
            else:
                fname = os.path.basename(path)
                fpath = os.path.join(binfo["raw_images"], fname)
            if os.path.exists(fpath):
                self.send_file(fpath, "image/jpeg")
            else:
                self.send_error(404, "Image not found")
            return

        if path == "/api/book":
            ensure_fresh_compilation(book_key)
            if os.path.exists(binfo["master_json"]):
                self.send_file(binfo["master_json"], "application/json; charset=utf-8")
            else:
                bcfg = get_book_cfg(book_key)
                self.send_json({
                    "book_key": book_key,
                    "title_geez": bcfg.get("title_geez", ""),
                    "stats": {"total_pdf_pages": bcfg.get("total_pages", 0), "extracted_pages_count": 0},
                    "chapters": [],
                    "chapter_index": [],
                    "topical_index": [],
                    "stage2_corrections": [],
                    "uncertain_apparatus": [],
                })
            return

        if path.startswith("/api/page/"):
            try:
                p_num = int(path.split("/api/page/")[1])
                p_path = os.path.join(binfo["pages_dir"], f"page_{p_num:03d}.json")
                if os.path.exists(p_path):
                    self.send_file(p_path, "application/json; charset=utf-8")
                else:
                    self.send_json({"error": f"Page {p_num} not extracted yet", "pdf_page": p_num}, status=404)
            except ValueError:
                self.send_error(400, "Invalid page number")
            return

        if path == "/api/search":
            q = (qs.get("q", [""])[0]).strip()
            ensure_fresh_compilation(book_key)
            if not q or not os.path.exists(binfo["master_json"]):
                self.send_json({"results": []})
                return
            book = json.load(open(binfo["master_json"], encoding="utf-8"))
            results = []
            for ch in book.get("chapters", []):
                for v in ch.get("verses", []):
                    plain = v.get("rejoined_plain_text", "")
                    if q in plain or (v.get("section_title") and q in v["section_title"]):
                        results.append({
                            "chapter_num": ch["chapter_num"],
                            "chapter_ethiopic": ch["chapter_ethiopic"],
                            "verse_num": v["verse_num"],
                            "verse_ethiopic": v["verse_ethiopic"],
                            "start_pdf_page": v["start_pdf_page"],
                            "start_book_page_ethiopic": v["start_book_page_ethiopic"],
                            "section_title": v.get("section_title"),
                            "geez_root_lemmas": v.get("geez_root_lemmas", []),
                            "rejoined_marked_text": v.get("rejoined_marked_text", ""),
                        })
                        if len(results) >= 100:
                            break
                if len(results) >= 100:
                    break
            self.send_json({"query": q, "count": len(results), "results": results})
            return

        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/update_line":
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            book_key = body.get("book", "matewes").strip().lower()
            if book_key not in BOOK_PATHS:
                book_key = "matewes"
            binfo = BOOK_PATHS[book_key]
            pdf_page = int(body["pdf_page"])
            col_idx = int(body["column_index"])
            line_num = int(body["line_num"])
            new_text = body["text"]
            resolve_uncertain = body.get("resolve_uncertain", False)

            p_path = os.path.join(binfo["pages_dir"], f"page_{pdf_page:03d}.json")
            if not os.path.exists(p_path):
                self.send_json({"error": "Page JSON not found"}, status=404)
                return

            p_data = json.load(open(p_path, encoding="utf-8"))
            updated = False
            for col in p_data.get("columns", []):
                if col.get("column_index") == col_idx:
                    for ln in col.get("lines", []):
                        if ln.get("line_num") == line_num:
                            ln["text"] = new_text
                            if resolve_uncertain:
                                ln["uncertain"] = []
                            updated = True
                            break
            if updated:
                with open(p_path, "w", encoding="utf-8") as f:
                    json.dump(p_data, f, ensure_ascii=False, indent=2)
                recompile_book(book_key)
                _last_compiled_counts[book_key] = len(glob.glob(os.path.join(binfo["pages_dir"], "page_*.json")))
                self.send_json({"ok": True, "book": book_key, "pdf_page": pdf_page, "column_index": col_idx, "line_num": line_num})
            else:
                self.send_json({"error": "Line not found"}, status=404)
            return

        self.send_error(404, "Endpoint not found")

    def send_file(self, fpath: str, content_type: str):
        with open(fpath, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    ensure_fresh_compilation("matewes")
    print(f"📖 Complete 13-Book New Testament Ge'ez & Andemta Studio running at http://localhost:{PORT}")
    server = ThreadingHTTPServer(("0.0.0.0", PORT), AndemtaRequestHandler)
    server.serve_forever()
