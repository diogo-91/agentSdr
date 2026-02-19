"""
Cliente para a Grok AI (xAI) — compatível com OpenAI SDK.
"""
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from core.config import settings
from core.logger import logger
from core.exceptions import GrokAPIError


class GrokClient:
    # URL padrão xAI, mas pode ser sobrescrita por env var (para OpenRouter)
    DEFAULT_BASE_URL = "https://api.x.ai/v1"

    def __init__(self):
        # Prioriza a URL do OpenRouter se definida no .env, senão usa xAI
        base_url = settings.openrouter_base_url or self.DEFAULT_BASE_URL
        
        self.client = OpenAI(
            api_key=settings.grok_api_key,
            base_url=base_url,
        )
        self.model = settings.grok_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
    ) -> dict:
        """
        Envia mensagens para o Grok e retorna a resposta completa.
        Suporta function calling via tools.
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.85,       # Um pouco de criatividade para parecer humano
                "max_tokens": 1024,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice

            logger.debug(f"Chamando Grok com {len(messages)} mensagens no histórico")
            response = self.client.chat.completions.create(**kwargs)
            logger.debug(f"Grok respondeu: finish_reason={response.choices[0].finish_reason}")
            return response

        except Exception as e:
            logger.error(f"Erro na Grok API: {e}")
            raise GrokAPIError(f"Falha na comunicação com Grok: {e}")


# Instância global
grok_client = GrokClient()
