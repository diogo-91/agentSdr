"""
Cliente Evolution API — envio de mensagens, documentos e indicador de digitação.
"""
import asyncio
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.config import settings
from core.logger import logger
from core.exceptions import EvolutionAPIError


class EvolutionClient:
    def __init__(self):
        self.base_url = settings.evolution_api_url.rstrip("/")
        self.instance = settings.evolution_instance
        self.headers = {
            "apikey": settings.evolution_api_key,
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    async def send_text(self, phone: str, message: str) -> dict:
        """Envia mensagem de texto para um número."""
        url = f"{self.base_url}/message/sendText/{self.instance}"
        payload = {
            "number": phone,
            "text": message,
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                logger.info(f"Mensagem enviada para {phone[:8]}***")
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP Evolution API [{e.response.status_code}]: {e.response.text}")
            raise EvolutionAPIError(f"Erro HTTP {e.response.status_code}: {e.response.text}")
        except httpx.HTTPError as e:
            logger.error(f"Erro de conexão Evolution API: {e}")
            raise EvolutionAPIError(f"Erro de conexão: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    async def send_document_url(self, phone: str, url_doc: str, caption: str, filename: str) -> dict:
        """Envia um documento (PDF) via URL."""
        url = f"{self.base_url}/message/sendMedia/{self.instance}"
        payload = {
            "number": phone,
            "mediatype": "document",
            "mimetype": "application/pdf",
            "caption": caption,
            "media": url_doc,
            "fileName": filename,
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                logger.info(f"Documento enviado para {phone[:8]}***")
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro ao enviar documento [{e.response.status_code}]: {e.response.text}")
            raise EvolutionAPIError(f"Erro HTTP {e.response.status_code}: {e.response.text}")

    async def send_typing(self, phone: str, duration_ms: int = 2000):
        """Simula indicador de digitação (experience humana)."""
        url = f"{self.base_url}/chat/sendPresence/{self.instance}"
        payload = {
            "number": phone,
            "options": {
                "presence": "composing",
                "delay": duration_ms,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(url, json=payload, headers=self.headers)
        except Exception as e:
            # Não crítico — só loga e continua
            logger.debug(f"Falha ao enviar typing indicator: {e}")

    async def send_message_humanized(self, phone: str, message: str):
        """
        Envia mensagem com simulação de digitação proporcional ao tamanho da mensagem.
        Torna a conversa mais natural e humana.
        """
        # Calcula delay baseado no tamanho (mínimo 1s, máximo 4s)
        char_count = len(message)
        delay_ms = min(max(char_count * 30, 1000), 4000)

        await self.send_typing(phone, delay_ms)
        await asyncio.sleep(delay_ms / 1000)
        await self.send_text(phone, message)


# Instância global
evolution_client = EvolutionClient()
