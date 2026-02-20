"""
Orquestrador principal do agente SDR Ana Laura.
Gerencia o ciclo completo: recebe mensagem → carrega memória → chama Grok → executa tools → responde.
"""
import json
import asyncio

from core.config import settings
from core.logger import logger
from core.exceptions import GrokAPIError, EvolutionAPIError, SDRAgentError
from integrations.grok_client import grok_client
from integrations.evolution_client import evolution_client
from agent.persona import get_system_prompt
from agent.memory import memory
from agent.tools import TOOLS_DEFINITION, execute_tool


# Mensagem de fallback caso tudo falhe
# Mensagem de fallback caso tudo falhe (neutra e profissional)
FALLBACK_MESSAGE = (
    "Desculpe, não consegui processar sua mensagem agora. "
    "Poderia tentar novamente em alguns instantes?"
)

# Máximo de iterações de tool calling por mensagem (evita loops)
MAX_TOOL_ITERATIONS = 8

# Padrões de mensagens simples que NÃO precisam de tool calls
# ATENÇÃO: não incluir confirmações ("sim", "ok", "certo") — podem acionar gerar_orcamento
_SIMPLE_MESSAGE_PATTERNS = [
    "oi", "olá", "ola", "bom dia", "boa tarde", "boa noite",
    "obrigado", "obrigada", "valeu", "até mais", "tchau",
    "até logo", "flw", "👍", "❤️", "😊", "🙏",
]

def _is_simple_message(message: str) -> bool:
    """Retorna True APENAS para saudações puras sem intenção de ação."""
    cleaned = message.strip().lower()

    # Apenas saudações exatas bloqueiam tools
    if any(cleaned == pat or cleaned.startswith(pat + "!") or cleaned.startswith(pat + ",") for pat in _SIMPLE_MESSAGE_PATTERNS):
        return True

    # Termos que indicam intenção de ação — nunca bloquear tools
    action_hints = [
        "preço", "preco", "valor", "telha", "calha", "metalon",
        "orçamento", "orcamento", "quanto", "comprar", "produto",
        "gerar", "montar", "fazer", "enviar", "manda", "quero",
        "pode", "sim", "confirma", "confirmar", "fecha", "fechar",
        "pedido", "compra", "pagar", "entrega",
    ]

    # Mensagem curta sem nenhuma intenção de ação → simples
    words = cleaned.split()
    if len(words) <= 3 and not any(hint in cleaned for hint in action_hints):
        return True

    return False


class SDRAgent:
    """Agente SDR humanizado com memória persistente e function calling."""

    async def process_message(
        self,
        phone: str,
        message: str,
        sender_name: str | None = None,
    ) -> None:
        """
        Processa uma mensagem recebida e envia a resposta ao cliente.

        Args:
            phone: Número do cliente (formato: 5511999999999)
            message: Texto da mensagem recebida
            sender_name: Nome do remetente (se disponível no webhook)
        """
        logger.info(f"Processando mensagem de {phone[:8]}*** | Nome: {sender_name or 'desconhecido'}")

        try:
            # 1. Get/create lead
            lead = memory.get_or_create_lead(phone=phone, name=sender_name)
            lead_id = lead["id"]

            # 2. Salva mensagem do usuário
            memory.save_message(lead_id=lead_id, role="user", content=message)

            # 3. Carrega histórico de conversação
            history = memory.get_history(lead_id=lead_id)

            # Context para as tools e prompt
            has_orcamento = memory.has_orcamento(lead_id)
            context = {
                "lead_id": lead_id,
                "phone": phone,
                "lead_name": lead.get("nome"),
                "has_orcamento": has_orcamento,
            }

            # 4. Simula typing enquanto processa
            asyncio.create_task(evolution_client.send_typing(phone, 3000))

            # 5. Executa o loop do agente (suporta tool calling em cadeia)
            response_text = await self._agent_loop(
                history=history,
                context=context,
                last_message=message,
            )

            # 6. Salva resposta do assistente
            if response_text:
                memory.save_message(lead_id=lead_id, role="assistant", content=response_text)

            # 7. Envia resposta humanizada ao cliente
            if response_text:
                await evolution_client.send_message_humanized(phone=phone, message=response_text)

        except GrokAPIError as e:
            logger.error(f"Erro Grok API: {e}")
            await self._send_fallback(phone)

        except EvolutionAPIError as e:
            logger.error(f"Erro Evolution API ao responder: {e}")
            # Não há o que fazer se o WhatsApp está fora

        except Exception as e:
            logger.exception(f"Erro inesperado ao processar mensagem: {e}")
            await self._send_fallback(phone)

    async def _agent_loop(self, history: list[dict], context: dict, last_message: str = "") -> str | None:
        """
        Loop de raciocínio do agente com suporte a tool calling em cadeia.
        Limita a MAX_TOOL_ITERATIONS chamadas de tool por rodada.
        """
        system_prompt = get_system_prompt(customer_name=context.get("lead_name"))
        messages = [
            {"role": "system", "content": system_prompt},
            *history,
        ]

        # Se já existe orçamento para este lead, remove a tool gerar_orcamento
        # para evitar que o Grok gere um novo PDF em resposta a agradecimentos
        available_tools = [
            t for t in TOOLS_DEFINITION
            if not (t["function"]["name"] == "gerar_orcamento" and context.get("has_orcamento"))
        ]
        if context.get("has_orcamento"):
            logger.info("Lead já possui orçamento — tool gerar_orcamento desabilitada para este turno.")

        # Se a mensagem for uma saudação/resposta simples, bloqueia tool calls
        # para resposta imediata sem consultar a planilha
        is_simple = _is_simple_message(last_message)
        if is_simple:
            logger.info(f"Mensagem simples detectada — tool_choice=none para resposta direta.")

        iterations = 0
        tool_results_for_history = []

        while iterations < MAX_TOOL_ITERATIONS:
            iterations += 1

            # Bloqueia tools para mensagens simples (saudações, agradecimentos)
            effective_tool_choice = "none" if is_simple else ("auto" if available_tools else "none")
            effective_tools = available_tools if not is_simple else []

            response = grok_client.chat(
                messages=messages,
                tools=effective_tools,
                tool_choice=effective_tool_choice,
            )

            choice = response.choices[0]
            finish_reason = choice.finish_reason
            msg = choice.message

            # Resposta de texto final
            if finish_reason == "stop" or not msg.tool_calls:
                if msg.content:
                    return msg.content
                # Caso raro: sem conteúdo e sem tool calls
                logger.warning("Grok retornou resposta vazia sem tool calls.")
                return None

            # ── Tool calling ──
            if finish_reason == "tool_calls" or msg.tool_calls:
                # Adiciona a mensagem do assistente com tool calls ao contexto
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })

                # Executa todas as tools chamadas (pode ser mais de uma em paralelo)
                tool_tasks = []
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        tool_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    tool_tasks.append(
                        (tool_call.id, tool_name, execute_tool(tool_name, tool_args, context))
                    )

                # Executa em paralelo
                results = await asyncio.gather(
                    *[task[2] for task in tool_tasks],
                    return_exceptions=True,
                )

                # Adiciona resultados ao contexto
                tool_results_to_save = []
                for i, (tool_call_id, tool_name, _) in enumerate(tool_tasks):
                    result = results[i]
                    if isinstance(result, Exception):
                        result_str = json.dumps({"erro": str(result)})
                        logger.error(f"Tool {tool_name} falhou: {result}")
                    else:
                        result_str = result

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result_str,
                    })

                    # Persiste tool results importantes (gerar_orcamento) no banco
                    # para que o Grok saiba em conversas futuras que o orçamento foi enviado
                    if tool_name == "gerar_orcamento":
                        try:
                            import json as _json
                            result_data = _json.loads(result_str) if isinstance(result_str, str) else {}
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
                        except Exception as _e:
                            logger.debug(f"Não foi possível persistir tool result: {_e}")

                    logger.debug(f"Tool {tool_name} resultado: {result_str[:200]}")

                continue  # Volta ao loop para Grok processar o resultado

        # Se chegou aqui, excedeu o limite de iterações
        logger.warning(f"Excedido MAX_TOOL_ITERATIONS ({MAX_TOOL_ITERATIONS})")
        return "Oi! Estou finalizando o processamento, só um segundo! 😊"

    async def _send_fallback(self, phone: str):
        """Envia mensagem de fallback em caso de erro crítico."""
        try:
            await evolution_client.send_text(phone=phone, message=FALLBACK_MESSAGE)
        except Exception as e:
            logger.error(f"Falha ao enviar fallback para {phone[:8]}***: {e}")


# Instância global do agente
sdr_agent = SDRAgent()
