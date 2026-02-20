"""
Ferramentas (tools) disponíveis para o agente Ana Laura.
Definição para function calling do Grok + implementação.
"""
import json
from datetime import datetime, timedelta

from core.config import settings
from core.logger import logger
from core.exceptions import GoogleSheetsError, PDFGenerationError, EvolutionAPIError
from integrations.sheets_client import sheets_client
from integrations.evolution_client import evolution_client
from agent.memory import memory
from pdf.generator import pdf_generator


# ============================================================
# DEFINIÇÃO DAS TOOLS (formato OpenAI function calling)
# ============================================================

TOOLS_DEFINITION = [
    {
        "type": "function",
        "function": {
            "name": "consultar_precos",
            "description": (
                "Consulta a tabela de preços de produtos na planilha. "
                "Use SOMENTE quando o cliente perguntar explicitamente sobre preço, valor ou produto específico, "
                "ou quando for montar um orçamento a pedido do cliente. "
                "NÃO use para saudações, mensagens genéricas ou quando o cliente não demonstrou interesse em produto. "
                "Retorna lista com produto, unidade e preço unitário."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "busca": {
                        "type": "string",
                        "description": (
                            "Termo de busca para encontrar o produto. "
                            "Ex: 'telha galvalume', 'metalon', 'porta metalica', 'calha'. "
                            "Seja genérico para buscar múltiplos resultados."
                        ),
                    },
                },
                "required": ["busca"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gerar_orcamento",
            "description": (
                "Gera um orçamento em PDF e o envia ao cliente pelo WhatsApp. "
                "Use somente quando o cliente confirmar os itens e quantidades que deseja. "
                "Você deve ter coletado: nome do cliente, itens com quantidades, e opcionalmente cidade."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_cliente": {
                        "type": "string",
                        "description": "Nome completo ou primeiro nome do cliente.",
                    },
                    "itens": {
                        "type": "array",
                        "description": "Lista de itens do orçamento.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "produto": {"type": "string", "description": "Nome exato do produto conforme a planilha."},
                                "quantidade": {"type": "number", "description": "Quantidade solicitada."},
                                "unidade": {"type": "string", "description": "Unidade de medida (UNIDADE, METROS, KG)."},
                                "preco_unitario": {"type": "number", "description": "Preço unitário em reais."},
                            },
                            "required": ["produto", "quantidade", "unidade", "preco_unitario"],
                        },
                    },
                    "observacoes": {
                        "type": "string",
                        "description": "Observações adicionais para o orçamento (opcional).",
                    },
                },
                "required": ["nome_cliente", "itens"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notificar_gestor",
            "description": (
                "Notifica o gestor de vendas via WhatsApp com um resumo do lead e orçamento. "
                "Use quando o cliente demonstrar interesse em fechar negócio ou pedir negociação. "
                "Envie ANTES de informar ao cliente que o consultor vai entrar em contato."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_cliente": {
                        "type": "string",
                        "description": "Nome do cliente.",
                    },
                    "telefone_cliente": {
                        "type": "string",
                        "description": "Telefone do cliente.",
                    },
                    "resumo_interesse": {
                        "type": "string",
                        "description": "Resumo do que o cliente quer comprar e contexto da conversa.",
                    },
                    "valor_orcamento": {
                        "type": "number",
                        "description": "Valor total do orçamento em reais (0 se ainda não foi gerado).",
                    },
                    "pdf_url": {
                        "type": "string",
                        "description": "URL do PDF do orçamento (vazio se não gerado ainda).",
                    },
                },
                "required": ["nome_cliente", "telefone_cliente", "resumo_interesse", "valor_orcamento"],
            },
        },
    },
]


# ============================================================
# IMPLEMENTAÇÃO DAS TOOLS
# ============================================================

async def execute_tool(tool_name: str, tool_args: dict, context: dict) -> str:
    """
    Executa a tool chamada pelo Grok e retorna o resultado como string.
    context: {"lead_id": str, "phone": str}
    """
    logger.info(f"Executando tool: {tool_name} | args: {json.dumps(tool_args, ensure_ascii=False)[:200]}")

    if tool_name == "consultar_precos":
        return await _tool_consultar_precos(tool_args)

    elif tool_name == "gerar_orcamento":
        return await _tool_gerar_orcamento(tool_args, context)

    elif tool_name == "notificar_gestor":
        return await _tool_notificar_gestor(tool_args, context)

    else:
        logger.warning(f"Tool desconhecida: {tool_name}")
        return json.dumps({"erro": f"Tool '{tool_name}' não reconhecida."})


async def _tool_consultar_precos(args: dict) -> str:
    """Busca produtos na planilha e retorna JSON com resultados."""
    busca = args.get("busca", "")

    try:
        produtos = sheets_client.search_products(busca, limit=15)

        if not produtos:
            return json.dumps({
                "encontrados": 0,
                "mensagem": f"Nenhum produto encontrado para '{busca}'. Tente um termo mais genérico.",
                "produtos": [],
            }, ensure_ascii=False)

        return json.dumps({
            "encontrados": len(produtos),
            "busca": busca,
            "produtos": produtos,
        }, ensure_ascii=False)

    except GoogleSheetsError as e:
        logger.error(f"Erro ao consultar preços: {e}")
        return json.dumps({"erro": "Não consegui acessar a tabela de preços agora. Tente novamente."})


async def _tool_gerar_orcamento(args: dict, context: dict) -> str:
    """Gera PDF do orçamento e envia ao cliente."""
    nome_cliente = args.get("nome_cliente", "Cliente")
    itens = args.get("itens", [])
    observacoes = args.get("observacoes", "")
    lead_id = context.get("lead_id")
    phone = context.get("phone")

    if not itens:
        # FALLBACK: Se o LLM enviou parâmetros simplificados (produto, metragem)
        produto_nome = args.get("produto") or args.get("tipo_obra") # O LLM às vezes confunde
        metragem_raw = args.get("metragem") or args.get("quantidade")
        
        if produto_nome and metragem_raw:
            logger.info(f"Parametros simplificados detectados: produto={produto_nome}, metragem={metragem_raw}")
            # Tenta buscar o produto na planilha
            resultados = sheets_client.search_products(produto_nome, limit=1)
            if resultados:
                p = resultados[0]
                # Limpa a metragem (remove 'm', 'm2', etc)
                import re
                metragem_clean = re.sub(r"[^0-9,.]", "", str(metragem_raw)).replace(",", ".")
                try:
                    quantidade = float(metragem_clean)
                except ValueError:
                    quantidade = 1.0
                
                itens = [{
                    "produto": p["produto"],
                    "quantidade": quantidade,
                    "unidade": p["unidade"],
                    "preco_unitario": p["preco"]
                }]
                logger.info(f"Item gerado automaticamente: {itens[0]}")
            else:
                return json.dumps({"erro": f"Não encontrei o produto '{produto_nome}' na planilha para gerar o orçamento."})
        else:
            return json.dumps({"erro": "Nenhum item fornecido para o orçamento e parâmetros simplificados incompletos."})

    try:
        # Calcula totais
        for item in itens:
            item["total"] = round(item["quantidade"] * item["preco_unitario"], 2)

        valor_total = round(sum(i["total"] for i in itens), 2)
        validade = (datetime.now() + timedelta(days=settings.quote_validity_days)).strftime("%d/%m/%Y")

        # Número do orçamento
        numero = f"ORC-{datetime.now().strftime('%Y%m%d%H%M')}"

        # Gera PDF
        pdf_bytes = pdf_generator.generate(
            numero=numero,
            nome_cliente=nome_cliente,
            itens=itens,
            valor_total=valor_total,
            validade=validade,
            observacoes=observacoes,
        )

        # Upload para Supabase Storage
        pdf_url = _upload_pdf_supabase(pdf_bytes, f"{numero}.pdf")

        # Salva no banco
        if lead_id:
            memory.save_orcamento(
                lead_id=lead_id,
                itens=itens,
                valor_total=valor_total,
                pdf_url=pdf_url,
                observacoes=observacoes,
            )
            memory.update_lead(lead_id, {"status": "orcamento_enviado"})

        # Envia PDF ao cliente
        if phone and pdf_url:
            await evolution_client.send_document_url(
                phone=phone,
                url_doc=pdf_url,
                caption=f"📄 Orçamento {numero} - {settings.company_name}",
                filename=f"Orcamento_{nome_cliente.replace(' ', '_')}.pdf",
            )

        # Notifica o gestor automaticamente após o orçamento ser gerado
        if settings.manager_phone:
            try:
                resumo = f"Orçamento {numero} gerado.\nItens: {', '.join(i.get('descricao', '') for i in itens)}"
                await _tool_notificar_gestor(
                    args={
                        "nome_cliente": nome_cliente,
                        "telefone_cliente": phone or "",
                        "resumo_interesse": resumo,
                        "valor_orcamento": valor_total,
                        "pdf_url": pdf_url,
                    },
                    context=context,
                )
            except Exception as e:
                logger.warning(f"Notificação ao gestor falhou (não crítico): {e}")

        return json.dumps({
            "sucesso": True,
            "numero": numero,
            "valor_total": valor_total,
            "pdf_url": pdf_url,
            "validade": validade,
            "mensagem": f"Orçamento {numero} gerado e enviado com sucesso! Total: R$ {valor_total:,.2f}",
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Erro ao gerar orçamento: {e}")
        return json.dumps({
            "erro": f"Não foi possível gerar o orçamento: {str(e)}",
        }, ensure_ascii=False)


async def _tool_notificar_gestor(args: dict, context: dict) -> str:
    """Envia notificação para o gestor de vendas."""
    nome = args.get("nome_cliente", "Cliente")
    # Tenta pegar do argumento, senão do contexto
    telefone = args.get("telefone_cliente") or context.get("phone", "")
    resumo = args.get("resumo_interesse", "")
    valor = args.get("valor_orcamento", 0)
    pdf_url = args.get("pdf_url", "")
    lead_id = context.get("lead_id")

    # Se dados do orçamento não vieram, tenta buscar o último gerado no banco
    if (not valor or not pdf_url) and lead_id:
        orcamento = memory.get_last_orcamento(lead_id)
        if orcamento:
            if not valor:
                valor = orcamento.get("valor_total", 0)
            if not pdf_url:
                pdf_url = orcamento.get("pdf_url", "")
            logger.info("Dados do orçamento recuperados do banco para notificação.")

    try:
        valor_str = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if valor > 0 else "Não gerado ainda"

        mensagem = (
            f"🔔 *NOVO LEAD QUENTE!*\n\n"
            f"👤 *Cliente:* {nome}\n"
            f"📱 *Telefone:* {telefone}\n"
            f"💰 *Valor orçado:* {valor_str}\n\n"
            f"📋 *Interesse:*\n{resumo}\n\n"
        )

        if pdf_url:
            mensagem += f"📄 *PDF:* {pdf_url}\n\n"

        mensagem += f"_Atendido pela {settings.agent_name} • {datetime.now().strftime('%d/%m/%Y %H:%M')}_"

        await evolution_client.send_text(
            phone=settings.manager_phone,
            message=mensagem,
        )

        # Envia PDF também para o gestor se disponível
        if pdf_url:
            await evolution_client.send_document_url(
                phone=settings.manager_phone,
                url_doc=pdf_url,
                caption=f"Orçamento do cliente {nome}",
                filename=f"Orcamento_{nome.replace(' ', '_')}.pdf",
            )

        logger.info(f"Gestor notificado sobre lead: {nome}")
        return json.dumps({"sucesso": True, "mensagem": "Gestor notificado com sucesso."})

    except EvolutionAPIError as e:
        logger.error(f"Erro ao notificar gestor: {e}")
        return json.dumps({"erro": f"Falha ao notificar gestor: {str(e)}"})


def _upload_pdf_supabase(pdf_bytes: bytes, filename: str) -> str:
    """Faz upload do PDF para o Supabase Storage e retorna a URL pública."""
    from db.supabase_client import supabase
    from core.config import settings

    try:
        bucket = "orcamentos"
        path = f"pdfs/{filename}"

        supabase.storage.from_(bucket).upload(
            path=path,
            file=pdf_bytes,
            file_options={"content-type": "application/pdf", "upsert": "true"},
        )

        # URL pública
        public_url = supabase.storage.from_(bucket).get_public_url(path)
        logger.info(f"PDF enviado para Storage: {path}")
        return public_url

    except Exception as e:
        logger.error(f"Erro ao fazer upload do PDF: {e}")
        # Retorna string vazia — o orçamento ainda foi salvo no DB
        return ""
