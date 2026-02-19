"""
Webhook FastAPI para receber mensagens da Evolution API.
"""
import asyncio
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel

from core.logger import logger
from core.config import settings
from agent.sdr_agent import sdr_agent


router = APIRouter()


class EvolutionPayload(BaseModel):
    """Schema flexível do payload da Evolution API."""
    event: str | None = None
    instance: str | None = None
    data: dict | None = None


def _extract_message_data(payload: dict) -> tuple[str | None, str | None, str | None]:
    """
    Extrai phone, message, sender_name do payload da Evolution API.
    Retorna (phone, message, sender_name) ou (None, None, None) se inválido.
    """
    try:
        # Estrutura padrão Evolution API v2
        data = payload.get("data", {})
        key = data.get("key", {})
        message_obj = data.get("message", {})
        push_name = data.get("pushName") or data.get("notifyName")

        # Só processa mensagens recebidas (fromMe=False)
        if key.get("fromMe", False):
            return None, None, None

        # Extrai número do remoto
        remote_jid = key.get("remoteJid", "")
        if "@g.us" in remote_jid:
            # Ignora mensagens de grupo
            return None, None, None

        phone = remote_jid.replace("@s.whatsapp.net", "").replace("+", "")

        # Extrai texto da mensagem
        message_text = (
            message_obj.get("conversation")
            or message_obj.get("extendedTextMessage", {}).get("text")
            or message_obj.get("imageMessage", {}).get("caption")
            or "[Mídia recebida]"
        )

        return phone, message_text, push_name

    except Exception as e:
        logger.warning(f"Erro ao parsear payload Evolution: {e}")
        return None, None, None


async def _process_in_background(phone: str, message: str, sender_name: str | None):
    """Processa a mensagem em background (não bloqueia o webhook)."""
    try:
        await sdr_agent.process_message(
            phone=phone,
            message=message,
            sender_name=sender_name,
        )
    except Exception as e:
        logger.exception(f"Erro crítico no background process: {e}")


@router.post("/webhook/evolution")
async def webhook_handler(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint principal do webhook.
    Recebe eventos da Evolution API e processa de forma assíncrona.
    """
    try:
        payload = await request.json()
    except Exception:
        logger.warning("Payload inválido recebido no webhook")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = payload.get("event", "")
    logger.debug(f"Webhook recebido: event={event}")

    # Só processa eventos de mensagem recebida
    if event not in ("messages.upsert", "message", "messages.set"):
        return {"status": "ignored", "event": event}

    phone, message, sender_name = _extract_message_data(payload)

    if not phone or not message:
        logger.debug(f"Mensagem ignorada: phone={phone}, message={message}")
        return {"status": "ignored", "reason": "no_valid_message"}

    # Filtra mensagens muito curtas ou sem sentido
    if message.strip() == "[Mídia recebida]":
        logger.debug("Mídia sem texto ignorada")
        return {"status": "ignored", "reason": "media_only"}

    logger.info(f"Mensagem recebida de {phone[:8]}*** | {message[:50]}...")

    # Processa em background para responder rapidamente ao Evolution
    background_tasks.add_task(
        asyncio.ensure_future,
        _process_in_background(phone, message, sender_name),
    )

    return {"status": "received", "phone": phone[:8] + "***"}


@router.get("/health")
async def health_check():
    """Health check para o EasyPanel / Docker."""
    return {
        "status": "healthy",
        "agent": settings.agent_name,
        "company": settings.company_name,
    }
