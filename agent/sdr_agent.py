"""
Orquestrador principal do agente SDR Ana Laura.
Gerencia o ciclo completo: recebe mensagem → carrega memória → chama Grok → executa tools → responde.
"""
import json
import asyncio
import re
import time
from datetime import datetime

from core.config import settings
from core.logger import logger
from core.exceptions import GrokAPIError, EvolutionAPIError, SDRAgentError
from integrations.grok_client import grok_client
from integrations.evolution_client import evolution_client
from agent.persona import get_system_prompt
from agent.memory import memory
from agent.tools import TOOLS_DEFINITION, execute_tool


# Mensagem de fallback profissional
FALLBACK_MESSAGE = (
    "Desculpe, não consegui processar sua mensagem agora. "
    "Poderia tentar novamente em alguns instantes?"
)

# Máximo de iterações de tool calling por mensagem (evita loops)
MAX_TOOL_ITERATIONS = 8

# Padrões de mensagens simples que NÃO precisam de tool calls
_SIMPLE_MESSAGE_PATTERNS = [
    "oi", "olá", "ola", "bom dia", "boa tarde", "boa noite",
    "obrigado", "obrigada", "valeu", "até mais", "tchau",
    "até logo", "flw", "👍", "❤️", "😊", "🙏",
]

def _is_simple_message(message: str) -> bool:
    """Retorna True APENAS para saudações puras sem intenção de ação."""
    cleaned = message.strip().lower()

    if any(cleaned == pat or cleaned.startswith(pat + "!") or cleaned.startswith(pat + ",") for pat in _SIMPLE_MESSAGE_PATTERNS):
        return True

    action_hints = [
        "preço", "preco", "valor", "telha", "calha", "metalon",
        "orçamento", "orcamento", "quanto", "comprar", "produto",
        "gerar", "montar", "fazer", "enviar", "manda", "quero",
        "pode", "sim", "confirma", "confirmar", "fecha", "fechar",
        "pedido", "compra", "pagar", "entrega",
    ]

    words = cleaned.split()
    if len(words) <= 3 and not any(hint in cleaned for hint in action_hints):
        return True

    return False


# Palavras que o agente usa ao OFERECER gerar o orçamento
_ORCAMENTO_OFFER_HINTS = [
    "quer que eu monte um orçamento",
    "posso montar um orçamento",
    "vou gerar o orçamento",
    "monte um orçamento",
    "orçamento inicial",
    "orçamento baseado",
    "posso seguir com o pedido",
]

# Palavras de confirmação do cliente para a oferta de orçamento
_ORCAMENTO_CONFIRM_HINTS = [
    "sim", "pode", "quero", "gera", "manda", "faz", "vai",
    "montar", "gerar", "fazer", "enviar", "orca", "orçamento",
    "pode sim", "claro", "vai lá", "vamos",
]


def _is_orcamento_confirmation(last_message: str, history: list[dict]) -> bool:
    """Retorna True se o cliente confirmou gerar o orçamento."""
    cleaned = last_message.strip().lower()
    is_confirm = any(hint in cleaned for hint in _ORCAMENTO_CONFIRM_HINTS)
    if not is_confirm:
        return False

    last_assistant = ""
    for msg in reversed(history):
        if msg.get("role") == "assistant":
            last_assistant = msg.get("content", "").lower()
            break

    return any(hint in last_assistant for hint in _ORCAMENTO_OFFER_HINTS)


class SDRAgent:
    """Agente SDR profissional com memória persistente e segurança de saída."""

    async def process_message(
        self,
        phone: str,
        message: str,
        sender_name: str | None = None,
    ) -> None:
        logger.info(f"Processando mensagem de {phone[:8]}***")

        try:
            lead = memory.get_or_create_lead(phone=phone, name=sender_name)
            lead_id = lead["id"]
            memory.save_message(lead_id=lead_id, role="user", content=message)
            history = memory.get_history(lead_id=lead_id)

            has_orcamento = memory.has_orcamento(lead_id)
            context = {
                "lead_id": lead_id,
                "phone": phone,
                "lead_name": lead.get("nome"),
                "has_orcamento": has_orcamento,
            }

            asyncio.create_task(evolution_client.send_typing(phone, 2000))

            response_text = await self._agent_loop(
                history=history,
                context=context,
                last_message=message,
            )

            if response_text:
                memory.save_message(lead_id=lead_id, role="assistant", content=response_text)
                await evolution_client.send_message_humanized(phone=phone, message=response_text)

        except Exception as e:
            logger.exception(f"Erro ao processar mensagem: {e}")
            await self._send_fallback(phone)

    async def _agent_loop(self, history: list[dict], context: dict, last_message: str = "") -> str | None:
        system_prompt = get_system_prompt(customer_name=context.get("lead_name"))
        messages = [
            {"role": "system", "content": system_prompt},
            *history,
        ]

        available_tools = [
            t for t in TOOLS_DEFINITION
            if not (t["function"]["name"] == "gerar_orcamento" and context.get("has_orcamento"))
        ]

        is_simple = _is_simple_message(last_message)
        force_gerar_orcamento = (
            not context.get("has_orcamento")
            and _is_orcamento_confirmation(last_message, history)
        )

        iterations = 0
        while iterations < MAX_TOOL_ITERATIONS:
            iterations += 1

            if force_gerar_orcamento and iterations == 1:
                effective_tool_choice = {"type": "function", "function": {"name": "gerar_orcamento"}}
                effective_tools = [t for t in available_tools if t["function"]["name"] == "gerar_orcamento"]
                force_gerar_orcamento = False
            elif is_simple:
                effective_tool_choice = "none"
                effective_tools = []
            else:
                effective_tool_choice = "auto" if available_tools else "none"
                effective_tools = available_tools

            response = grok_client.chat(
                messages=messages,
                tools=effective_tools,
                tool_choice=effective_tool_choice,
            )

            choice = response.choices[0]
            finish_reason = choice.finish_reason
            msg = choice.message

            # 1. Resposta de Texto ou Intercepção de Tool Call em Texto
            if finish_reason == "stop" or not msg.tool_calls:
                if msg.content:
                    content = msg.content.strip()
                    
                    # Tenta interceptar chamadas que a IA fez via texto/JSON por erro
                    if "tool_name" in content:
                        logger.info("Intercepetando tool call em formato texto...")
                        json_match = re.search(r'(\{.*?"tool_name".*?\})', content, re.DOTALL)
                        if json_match:
                            try:
                                json_str = json_match.group(1)
                                tool_data = json.loads(json_str)
                                tool_name = tool_data.get("tool_name")
                                tool_args = tool_data.get("parameters") or tool_data.get("args") or {}
                                
                                if tool_name:
                                    fake_id = f"call_text_{int(time.time())}"
                                    messages.append({
                                        "role": "assistant",
                                        "content": msg.content,
                                        "tool_calls": [{"id": fake_id, "type": "function", "function": {"name": tool_name, "arguments": json.dumps(tool_args)}}]
                                    })
                                    result_str = await execute_tool(tool_name, tool_args, context)
                                    messages.append({"role": "tool", "tool_call_id": fake_id, "content": result_str})
                                    if tool_name == "gerar_orcamento":
                                        self._persist_orcamento_result(result_str, context)
                                    continue # Re-analisa com resultado da tool
                            except Exception as e:
                                logger.warning(f"Erro na intercepção: {e}")

                    # Se for texto puro, aplica limpeza de segurança contra vazamento de código
                    clean_content = re.sub(r'```.*?```', '', msg.content, flags=re.DOTALL).strip()
                    clean_content = re.sub(r'^\{.*\}$', '', clean_content, flags=re.MULTILINE).strip()
                    return clean_content if clean_content else "Como posso auxiliá-lo?"
                
                return None

            # 2. Resposta de Tool Call Nativa
            if finish_reason == "tool_calls" or msg.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        } for tc in msg.tool_calls
                    ],
                })

                tool_tasks = []
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}
                    tool_tasks.append((tool_call.id, tool_name, execute_tool(tool_name, tool_args, context)))

                results = await asyncio.gather(*[task[2] for task in tool_tasks], return_exceptions=True)

                for i, (tool_call_id, tool_name, _) in enumerate(tool_tasks):
                    result = results[i]
                    result_str = json.dumps({"erro": str(result)}) if isinstance(result, Exception) else result
                    messages.append({"role": "tool", "tool_call_id": tool_call_id, "content": result_str})
                    if tool_name == "gerar_orcamento":
                        self._persist_orcamento_result(result_str, context)

                continue # Volta ao loop para processar resultados

        return "Peço desculpas. Poderia reformular seu pedido?"

    def _persist_orcamento_result(self, result_str: str, context: dict) -> None:
        """Persiste o resultado da geração de orçamento no banco de dados."""
        try:
            result_data = json.loads(result_str) if isinstance(result_str, str) else {}
            if result_data.get("sucesso"):
                lead_id = context.get("lead_id")
                if lead_id:
                    memory.save_message(
                        lead_id=lead_id,
                        role="assistant",
                        content=(
                            f"[ORÇAMENTO ENVIADO] Número: {result_data.get('numero')} | "
                            f"Total: R$ {result_data.get('valor_total', 0):,.2f} | "
                            f"Validade: {result_data.get('validade')} | "
                            "Status: PDF enviado ao cliente com sucesso."
                        ),
                    )
        except Exception as e:
            logger.debug(f"Não foi possível persistir tool result: {e}")

    async def _send_fallback(self, phone: str):
        try:
            await evolution_client.send_text(phone=phone, message=FALLBACK_MESSAGE)
        except Exception as e:
            logger.error(f"Falha ao enviar fallback: {e}")

sdr_agent = SDRAgent()
