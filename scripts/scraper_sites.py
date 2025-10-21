# scripts/scraper_sites.py - Versão SIMPLIFICADA (Grava Local)

import requests
from bs4 import BeautifulSoup
import os
import logging
from time import sleep

# --- Configurações ---
# Pasta onde o arquivo de contexto será salvo (para ser comitado)
CONTEXT_DIR = "data/affix/raw" 
SITE_CONTEXT_FILENAME = "sites_context.txt"

# ... (Mantenha a lista URL_CATALOG e a função scrape_and_clean como estão) ...

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # Garante que a pasta de destino existe
    os.makedirs(CONTEXT_DIR, exist_ok=True)
    
    full_context = f"Contexto de Sites Oficiais Affix/Alter/Hapvida (Gerado em: {os.environ.get('GITHUB_RUN_ID', 'Local')})\n\n"
    
    # 1. Faz o scraping de todas as URLs
    for url in URL_CATALOG:
        context = scrape_and_clean(url)
        full_context += context + "\n\n"
        sleep(0.5) 

    # 2. Salva o arquivo localmente
    output_path = os.path.join(CONTEXT_DIR, SITE_CONTEXT_FILENAME)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_context)
        logging.info(f"Arquivo de contexto salvo localmente: {output_path}")
    except Exception as e:
        logging.error(f"Falha ao salvar o arquivo TXT localmente: {e}")
        return

    logging.info("Processo de scraping concluído com sucesso!")

if __name__ == "__main__":
    main()
