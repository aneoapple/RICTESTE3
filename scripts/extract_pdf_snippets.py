#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Lê PDFs e gera pdf_snippets.json com trechos úteis.
# Pastas lidas: data/affix/raw + outras via env PDF_DIRS="path1,path2"
import os, re, json, pathlib, sys
from datetime import datetime

try:
    import fitz  # PyMuPDF
except Exception:
    print("PyMuPDF não instalado. pip install pymupdf", file=sys.stderr); raise

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_DIRS = [ROOT / "data" / "affix" / "raw"]
EXTRA_DIRS = [pathlib.Path(p.strip()) for p in os.getenv("PDF_DIRS","").split(",") if p.strip()]
PDF_DIRS = [p for p in (DEFAULT_DIRS + EXTRA_DIRS) if p.exists()]

OUT_JSON = ROOT / "pdf_snippets.json"
MAX_CHARS = int(os.getenv("MAX_CHARS_PER_DOC","7000"))  # limite por doc
MIN_KEEP  = 400

KEYS = [r"document", r"regras", r"fluxo", r"prazo", r"envio", r"exigido", r"contato", r"email", r"anexo"]

def clean(s:str)->str:
    s = s.replace("\x00"," ")
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()

def score_block(b:str)->int:
    lb = b.lower()
    return sum(3 for k in KEYS if re.search(k, lb)) + min(len(b)//500, 6)

def best_chunks(txt:str)->str:
    blocks = re.split(r"\n{2,}", txt)
    blocks.sort(key=score_block, reverse=True)
    out, cur = [], 0
    for b in blocks:
        if cur >= MAX_CHARS: break
        out.append(b); cur += len(b)+2
    s = clean("\n\n".join(out))
    return s[:MAX_CHARS].rsplit("\n",1)[0] if len(s)>MAX_CHARS else s

def extract_pdf(p: pathlib.Path)->str:
    try:
        doc = fitz.open(p)
    except Exception:
        return ""
    pages = []
    for pg in doc:
        try:
            pages.append(pg.get_text("text"))
        except Exception:
            continue
    doc.close()
    txt = clean("\n".join(pages))
    if len(txt) <= MAX_CHARS:
        return txt
    return best_chunks(txt)

def main():
    items = []
    seen = set()
    for base in PDF_DIRS:
        for pdf in sorted(base.rglob("*.pdf")):
            if pdf.name in seen: continue
            seen.add(pdf.name)
            t = extract_pdf(pdf)
            if len(t) >= MIN_KEEP:
                items.append({"name": pdf.name, "snippets": t})
    OUT_JSON.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_JSON} ({len(items)} docs) at {datetime.utcnow().isoformat()}Z")

if __name__ == "__main__":
    main()
