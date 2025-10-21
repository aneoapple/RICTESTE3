#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baixa PDFs listados em data/affix/affix_pdfs_manifest.csv para data/affix/raw/.
Recomeça downloads idempotentes. Valida MIME e tamanho. Faz retry simples.
Dep.: pip install requests
"""
import csv, os, pathlib, time, requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "affix" / "affix_pdfs_manifest.csv"
OUTDIR = ROOT / "data" / "affix" / "raw"
UA = "RIC-CRION-PDFScraper/1.0 (+github-actions)"

OUTDIR.mkdir(parents=True, exist_ok=True)

def download(url, dest):
    for i in range(3):
        try:
            with requests.get(url, headers={"User-Agent": UA}, timeout=60, stream=True) as r:
                if r.status_code != 200:
                    raise RuntimeError(f"HTTP {r.status_code}")
                ctype = r.headers.get("Content-Type","").lower()
                if "pdf" not in ctype:
                    # alguns servidores mandam octet-stream: aceitar se extensão .pdf
                    if not url.lower().endswith(".pdf"):
                        raise RuntimeError(f"Content-Type inválido: {ctype}")
                size = int(r.headers.get("Content-Length","0") or 0)
                if size and size < 1024:  # evita lixo
                    raise RuntimeError(f"Arquivo muito pequeno: {size} bytes")
                tmp = dest.with_suffix(dest.suffix + ".part")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1024*64):
                        if chunk:
                            f.write(chunk)
                tmp.replace(dest)
                return
        except Exception as e:
            if i == 2:
                raise
            time.sleep(2*(i+1))

def main():
    if not MANIFEST.exists():
        raise SystemExit(f"Manifesto ausente: {MANIFEST}")
    with MANIFEST.open(encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            name = (row.get("name") or "").strip()
            url  = (row.get("url") or "").strip()
            if not name or not url:
                continue
            # sanitiza nome simples
            safe = name.replace("/", "_").replace("\\","_")
            dest = OUTDIR / safe
            # baixa se não existe ou está vazio
            if not dest.exists() or dest.stat().st_size < 1024:
                print(f"[DL] {url} -> {dest}")
                download(url, dest)
            else:
                print(f"[SKIP] {dest} já existe ({dest.stat().st_size} bytes)")
    # resumo
    n = len(list(OUTDIR.glob("*.pdf")))
    print(f"PDFs disponíveis em {OUTDIR}: {n}")

if __name__ == "__main__":
    main()
