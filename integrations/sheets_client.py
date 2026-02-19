"""
Cliente Google Sheets — leitura de produtos e preços.
Cache em memória para evitar chamadas excessivas à API.
"""
import json
import time
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials
from tenacity import retry, stop_after_attempt, wait_exponential

from core.config import settings
from core.logger import logger
from core.exceptions import GoogleSheetsError


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Cache simples em memória (TTL: 10 minutos)
_cache: dict = {"data": [], "timestamp": 0}
CACHE_TTL = 600  # segundos


class SheetsClient:
    def __init__(self):
        self._client: gspread.Client | None = None

    def _get_client(self) -> gspread.Client:
        if self._client is None:
            try:
                if settings.google_credentials_json:
                    logger.info("Usando credenciais via variável de ambiente (JSON).")
                    creds_dict = json.loads(settings.google_credentials_json)
                    credentials = Credentials.from_service_account_info(
                        creds_dict, scopes=SCOPES
                    )
                else:
                    creds_path = Path(settings.google_credentials_path)
                    if not creds_path.exists():
                        raise GoogleSheetsError(
                            f"Credenciais não encontradas. Configure GOOGLE_CREDENTIALS_JSON ou crie o arquivo {creds_path}"
                        )
                    credentials = Credentials.from_service_account_file(
                        str(creds_path), scopes=SCOPES
                    )
                
                self._client = gspread.authorize(credentials)
            except Exception as e:
                logger.error(f"Erro ao autenticar Google Sheets: {e}")
                raise GoogleSheetsError(f"Falha na autenticação Google Sheets: {e}")
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def get_all_products(self) -> list[dict]:
        """
        Retorna todos os produtos da planilha.
        Formato esperado: colunas [PRODUTO, UNIDADE, PREÇO]
        """
        now = time.time()
        if _cache["data"] and (now - _cache["timestamp"]) < CACHE_TTL:
            logger.debug("Retornando produtos do cache")
            return _cache["data"]

        try:
            client = self._get_client()
            spreadsheet = client.open_by_key(settings.google_sheets_id)
            worksheet = spreadsheet.sheet1

            records = worksheet.get_all_records()
            products = []

            for row in records:
                # Flexível: aceita variações nos nomes das colunas
                produto = (
                    row.get("PRODUTO") or row.get("Produto") or row.get("produto") or ""
                ).strip()
                unidade = (
                    row.get("UNIDADE") or row.get("Unidade") or row.get("unidade") or "UNIDADE"
                ).strip()
                preco_raw = (
                    row.get("PREÇO") or row.get("Preço") or row.get("preco") or row.get("PRECO") or "0"
                )

                if not produto:
                    continue

                # Limpa o preço: "R$ 44,13" → 44.13
                preco_str = str(preco_raw).strip()
                preco_str = preco_str.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
                try:
                    preco = float(preco_str)
                except ValueError:
                    preco = 0.0

                products.append({
                    "produto": produto,
                    "unidade": unidade,
                    "preco": preco,
                })

            _cache["data"] = products
            _cache["timestamp"] = now
            logger.info(f"Planilha carregada: {len(products)} produtos")
            return products

        except GoogleSheetsError:
            raise
        except Exception as e:
            logger.error(f"Erro ao ler Google Sheets: {e}")
            raise GoogleSheetsError(f"Falha ao ler planilha: {e}")

    def search_products(self, query: str, limit: int = 10) -> list[dict]:
        """
        Busca produtos por nome (case insensitive, partial match).
        Retorna os mais relevantes primeiro.
        """
        all_products = self.get_all_products()
        query_lower = query.lower()

        # Score por relevância
        scored = []
        for p in all_products:
            nome = p["produto"].lower()
            if query_lower in nome:
                # Score mais alto se começa com a query
                score = 2 if nome.startswith(query_lower) else 1
                scored.append((score, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    def invalidate_cache(self):
        """Força refresh do cache na próxima consulta."""
        _cache["timestamp"] = 0
        logger.info("Cache do Google Sheets invalidado")


# Instância global
sheets_client = SheetsClient()
