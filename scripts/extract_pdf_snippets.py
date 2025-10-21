#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lê PDFs em data/affix/raw, extrai texto e gera pdf_snippets.json.
Regras conservadoras: remove quebras excessivas, limita tamanho por arquivo.
Dep.: pip install pymupdf
"""
import json, os, re, sys, pathlib
from datetime import datetime

try:
    import fitz  # PyMuPDF
except Exception as e:
    print("ERROR: PyMuPDF não instalado. Adicione 'pymupdf' ao pip.", file=sys.stderr)
    raise

ROOT = pathlib.Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "data" / "affix" / "raw"
OUT_JSON = ROOT / "pdf_snippets.json"

MAX_CHARS_PER_DOC = int(os.getenv("MAX_CHARS_PER_DOC", "6000"))  # seguro p/ prompt
MIN_CHARS_KEEP = 400  # ignora PDFs vazios

KEY_ORDER = [
    r"^sum[aá]rio", r"^introdu", r"^objetivo", r"^escopo",
    r"fluxo", r"regras", r"documentos", r"prazo", r"observa", r"anexo"
]

def clean_text(s: str) -> str:
    s = s.replace("\x00", " ")
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = s.strip()
    return s

def rank_sections(txt: str) -> str:
    # Heurística simples: privilegia blocos que contêm palavras-chave conhecidas.
    blocks = re.split(r"\n{2,}", txt)
    scored = []
    for b in blocks:
        score = 0
        lb = b.lower()
        for i, k in enumerate(KEY_ORDER):
            if re.search(k, lb):
                score += (len(KEY_ORDER) - i) * 2
        score += min(len(b)//500, 5)  # um pouco de peso por tamanho
        scored.append((score, b))
    scored.sort(reverse=True, key=lambda x: x[0])
    top = "\n\n".join([b for _, b in scored[:12]])
    return top

def extract_pdf_text(pdf_path: pathlib.Path) -> str:
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return ""
    chunks = []
    for page in doc:
        try:
            chunks.append(page.get_text("text"))
        except Exception:
            continue
    doc.close()
    txt = clean_text("\n".join(chunks))
    if len(txt) <= MAX_CHARS_PER_DOC:
        return txt
    ranked = rank_sections(txt)
    ranked = clean_text(ranked)
    if len(ranked) > MAX_CHARS_PER_DOC:
        ranked = ranked[:MAX_CHARS_PER_DOC].rsplit("\n", 1)[0]
    return ranked

def main():
    if not PDF_DIR.exists():
        print(f"AVISO: pasta não existe: {PDF_DIR}", file=sys.stderr)
        OUT_JSON.write_text("[]", encoding="utf-8")
        return

    items = []
    for p in sorted(PDF_DIR.rglob("*.pdf")):
        text = extract_pdf_text(p)
        if len(text) < MIN_CHARS_KEEP:
            continue
        items.append({
            "name": p.name,
            "snippets": text
        })

    OUT_JSON.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_JSON} ({len(items)} docs) at {datetime.utcnow().isoformat()}Z")

if __name__ == "__main__":
    main()
