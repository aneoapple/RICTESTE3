# scripts/scraper_sites.py

import requests
from bs4 import BeautifulSoup
import os
import json
import logging
from time import sleep

# Dependências do Google Drive API
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# --- Configurações do Google Drive ---
# Você precisa configurar esta variável de ambiente no GitLab/GitHub Secrets
# Ex: GOOGLE_SA_CREDENTIALS = (conteúdo do seu JSON key da Service Account)
SERVICE_ACCOUNT_CREDENTIALS = os.environ.get('GOOGLE_SA_CREDENTIALS')
# ID da pasta MÃE onde o GAS busca os índices (MUDE ESTES VALORES!)
INDEX_FOLDER_NAME = "RIC_AI_INDEX" # Nome da pasta que o GAS procura, confira no seu Codigo GS
SITE_CONTEXT_FILENAME = "sites_context.txt"

# Escopos da API do Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- Configurações de Scraping ---
URL_CATALOG = [
    'https://www.affix.com.br/portal-do-parceiro/',
    'https://www.alter.com.br/portal-do-parceiro/',
    'https://www.hapvida.com.br/portal/',
    'https://www2.hapvida.com.br/segunda-via-de-boletos',
    # Adicione mais URLs importantes aqui para serem raspadas
    # Use as URLs da sua constante RIC_CONST.ALLOW_PREFIXES e RIC_CONST.URL_CATALOG_BASE
]

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_drive_service(creds_json):
    """Inicializa o serviço do Google Drive API v3."""
    try:
        info = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        logging.error(f"Erro ao inicializar o serviço do Drive: {e}")
        return None

def find_or_create_index_folder(service, folder_name):
    """Busca a pasta de índice pelo nome e a retorna ou a cria."""
    try:
        # Busca pasta pelo nome
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])

        if files:
            logging.info(f"Pasta '{folder_name}' encontrada: {files[0]['id']}")
            return files[0]['id']
        else:
            # Cria a pasta se não for encontrada
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            file = service.files().create(body=file_metadata, fields='id').execute()
            logging.warning(f"Pasta '{folder_name}' não encontrada. Criada nova pasta: {file.get('id')}")
            return file.get('id')

    except Exception as e:
        logging.error(f"Falha ao encontrar/criar a pasta de índice: {e}")
        return None

def upload_context_file(service, folder_id, content, filename):
    """Faz upload do arquivo de contexto para a pasta no Drive."""
    try:
        # 1. Checa se o arquivo já existe na pasta
        query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
        response = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        files = response.get('files', [])
        
        file_metadata = {'name': filename}
        media = MediaIoBaseUpload(io.BytesIO(content.encode('utf-8')), mimetype='text/plain', resumable=True)

        if files:
            # 2. Atualiza arquivo existente
            file_id = files[0]['id']
            service.files().update(fileId=file_id, body=file_metadata, media_body=media).execute()
            logging.info(f"Arquivo '{filename}' (ID: {file_id}) ATUALIZADO com sucesso.")
        else:
            # 3. Cria novo arquivo
            file_metadata['parents'] = [folder_id]
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            # Certifica que o arquivo é visível (se for a primeira vez)
            service.permissions().create(fileId=file.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()
            logging.info(f"Arquivo '{filename}' (ID: {file.get('id')}) CRIADO com sucesso.")

        return True
    except Exception as e:
        logging.error(f"Falha no upload/update do arquivo de contexto: {e}")
        return False

def scrape_and_clean(url):
    """Baixa a URL e limpa o HTML para extrair texto relevante."""
    try:
        logging.info(f"Raspando: {url}")
        headers = {'User-Agent': 'RIC-AI-Agent/3.0 (+github-actions-python)'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Lança erro para status HTTP ruim
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Remove elementos não-textuais ou de navegação
        for tag in soup(['script', 'style', 'header', 'nav', 'footer', 'aside', 'form']):
            tag.decompose()
        
        # Extrai o texto limpo, usando espaços em branco como delimitadores
        text = soup.get_text(separator=' ', strip=True)
        
        # Limpeza adicional: remover quebras de linha/múltiplos espaços e sanitizar caracteres
        text = ' '.join(text.split())
        
        return f"\n--- FONTE: {url} ---\n{text}"
        
    except requests.exceptions.RequestException as e:
        logging.warning(f"Falha ao raspar {url}: {e}")
        return f"\n--- FONTE (FALHA): {url} ---\n(Conteúdo indisponível)"
    except Exception as e:
        logging.error(f"Erro inesperado ao processar {url}: {e}")
        return f"\n--- FONTE (ERRO): {url} ---\n(Erro de processamento)"

def main():
    if not SERVICE_ACCOUNT_CREDENTIALS:
        logging.error("Variável de ambiente 'GOOGLE_SA_CREDENTIALS' não configurada. Abortando.")
        return

    full_context = f"Contexto de Sites Oficiais Affix/Alter/Hapvida (Gerado em: {os.environ.get('GITHUB_RUN_ID', 'GitLab/Local')})\n\n"
    
    # 1. Faz o scraping de todas as URLs
    for url in URL_CATALOG:
        context = scrape_and_clean(url)
        full_context += context + "\n\n"
        sleep(0.5) # Pausa para ser educado com os servidores

    # 2. Inicializa o serviço do Drive
    drive_service = get_drive_service(SERVICE_ACCOUNT_CREDENTIALS)
    if not drive_service:
        logging.error("Não foi possível conectar ao Google Drive.")
        return

    # 3. Encontra a pasta de destino
    index_folder_id = find_or_create_index_folder(drive_service, INDEX_FOLDER_NAME)
    if not index_folder_id:
        logging.error("Não foi possível encontrar/criar a pasta de índice no Drive.")
        return
        
    # 4. Faz o upload do arquivo de contexto
    success = upload_context_file(drive_service, index_folder_id, full_context, SITE_CONTEXT_FILENAME)
    
    if success:
        logging.info("Processo de scraping e upload concluído com sucesso!")
    else:
        logging.error("Processo de scraping falhou durante o upload.")

if __name__ == "__main__":
    main()
