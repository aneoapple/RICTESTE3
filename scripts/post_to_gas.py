#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Envia pdf_snippets.json + sites_context.txt ao GAS (doPost).
Requer: env GAS_URL=https://script.google.com/macros/s/XXXXX/exec
Dep.: pip install requests
"""
import os, json, pathlib, requests, sys
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
PDF_SNIPPETS = ROOT / "pdf_snippets.json"
SITES_CTX = ROOT / "sites_context.txt"
GAS_URL = os.environ.get("GAS_URL")
USER_QUERY = os.environ.get("USER_QUERY", "Teste automático: listar regras de emissão.")
USER_AGENT = os.environ.get("USER_AGENT", "github-actions")

def main():
    if not GAS_URL:
        print("GAS_URL não definido. Pulando envio.", file=sys.stderr)
        return

    pdf_list = []
    if PDF_SNIPPETS.exists():
        pdf_list = json.loads(PDF_SNIPPETS.read_text(encoding="utf-8"))

    sites_ctx = ""
    if SITES_CTX.exists():
        sites_ctx = SITES_CTX.read_text(encoding="utf-8")

    payload = {
        "q": USER_QUERY,
        "ua": USER_AGENT,
        "sites_context": sites_ctx,
        "pdf_snippets": pdf_list
    }

    r = requests.post(GAS_URL, json=payload, timeout=90)
    print("HTTP", r.status_code)
    print(r.text[:2000])
    if r.status_code >= 300:
        sys.exit(1)

if __name__ == "__main__":
    main()
