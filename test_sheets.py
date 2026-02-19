
import os
from google.oauth2.service_account import Credentials
import gspread

# Configuração
CREDENTIALS_FILE = 'credentials.json'
SHEET_ID = '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms'
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

def test_connection():
    print(f"--- Teste de Conexão Google Sheets ---")
    
    # 1. Verificar arquivo
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ Erro: Arquivo {CREDENTIALS_FILE} não encontrado.")
        return

    try:
        # 2. Autenticar
        print(f"1. Autenticando com {CREDENTIALS_FILE}...")
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        client = gspread.authorize(creds)
        print(f"✅ Autenticado como: {creds.service_account_email}")

        # 3. Listar arquivos acessíveis
        print("\n2. Listando planilhas acessíveis para esta conta...")
        files = client.list_spreadsheet_files()
        if not files:
            print("⚠️ Nenhuma planilha encontrada. A conta de serviço não tem acesso a nada.")
            print("   Certifique-se de compartilhar a planilha com o e-mail acima.")
        else:
            print(f"✅ Encontradas {len(files)} planilhas:")
            for f in files:
                print(f"   - [{f['id']}] {f['name']}")

        # 4. Tentar abrir a planilha específica
        print(f"\n3. Tentando abrir planilha ID: {SHEET_ID}...")
        try:
            sh = client.open_by_key(SHEET_ID)
            print(f"✅ Sucesso! Planilha aberta: '{sh.title}'")
            print(f"   Abas: {[w.title for w in sh.worksheets()]}")
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"❌ Erro: Planilha não encontrada (404).")
            print("   Verifique se o ID está correto e se o compartilhamento foi feito para o e-mail correto.")
        except Exception as e:
            print(f"❌ Erro ao abrir planilha: {e}")

    except Exception as e:
        print(f"❌ Erro geral: {e}")

if __name__ == "__main__":
    test_connection()
