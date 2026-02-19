"""
Gerenciamento de memória persistente do agente via Supabase.
"""
import uuid
from datetime import datetime
from core.logger import logger
from core.exceptions import SupabaseError
from core.config import settings
from db.supabase_client import supabase


class AgentMemory:
    """Gerencia leads e histórico de mensagens no Supabase."""

    # ===== LEADS =====

    def get_or_create_lead(self, phone: str, name: str | None = None) -> dict:
        """
        Retorna o lead existente ou cria um novo.
        Atualiza o nome se fornecido e ainda não estava salvo.
        """
        try:
            # Busca lead existente
            result = (
                supabase.table("leads")
                .select("*")
                .eq("telefone", phone)
                .execute()
            )

            if result.data:
                lead = result.data[0]
                # Atualiza nome se veio novo e ainda estava vazio
                if name and not lead.get("nome"):
                    updated = (
                        supabase.table("leads")
                        .update({"nome": name})
                        .eq("id", lead["id"])
                        .execute()
                    )
                    lead = updated.data[0]
                logger.debug(f"Lead existente encontrado: {lead['id']}")
                return lead

            # Cria novo lead
            new_lead = {
                "telefone": phone,
                "nome": name or None,
                "status": "novo",
            }
            result = supabase.table("leads").insert(new_lead).execute()
            lead = result.data[0]
            logger.info(f"Novo lead criado: {lead['id']} | {phone[:8]}***")
            return lead

        except Exception as e:
            logger.error(f"Erro ao get_or_create_lead: {e}")
            raise SupabaseError(f"Falha ao gerenciar lead: {e}")

    def update_lead(self, lead_id: str, data: dict) -> dict:
        """Atualiza campos do lead."""
        try:
            result = (
                supabase.table("leads")
                .update(data)
                .eq("id", lead_id)
                .execute()
            )
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f"Erro ao atualizar lead {lead_id}: {e}")
            raise SupabaseError(f"Falha ao atualizar lead: {e}")

    # ===== MENSAGENS =====

    def save_message(self, lead_id: str, role: str, content: str) -> dict:
        """Salva uma mensagem no histórico."""
        try:
            result = supabase.table("messages").insert({
                "lead_id": lead_id,
                "role": role,
                "content": content,
            }).execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f"Erro ao salvar mensagem: {e}")
            raise SupabaseError(f"Falha ao salvar mensagem: {e}")

    def get_history(self, lead_id: str, limit: int | None = None) -> list[dict]:
        """
        Retorna o histórico de mensagens formatado para a API do Grok.
        Formato: [{"role": "user"/"assistant", "content": "..."}]
        """
        try:
            max_msgs = limit or settings.max_history_messages
            result = (
                supabase.table("messages")
                .select("role, content, criado_em")
                .eq("lead_id", lead_id)
                .order("criado_em", desc=False)
                .limit(max_msgs)
                .execute()
            )

            history = []
            for msg in result.data:
                # Filtra apenas roles válidos para o Grok (user/assistant)
                if msg["role"] in ("user", "assistant"):
                    history.append({
                        "role": msg["role"],
                        "content": msg["content"],
                    })

            logger.debug(f"Histórico carregado: {len(history)} mensagens")
            return history

        except Exception as e:
            logger.error(f"Erro ao carregar histórico: {e}")
            return []  # Falha graciosamente — começa conversa sem histórico

    def is_returning_customer(self, lead_id: str) -> bool:
        """Verifica se o cliente já teve conversas anteriores."""
        try:
            result = (
                supabase.table("messages")
                .select("id", count="exact")
                .eq("lead_id", lead_id)
                .execute()
            )
            return (result.count or 0) > 0
        except Exception:
            return False

    # ===== ORÇAMENTOS =====

    def has_orcamento(self, lead_id: str) -> bool:
        """Verifica se o lead já possui ao menos um orçamento gerado."""
        try:
            result = (
                supabase.table("orcamentos")
                .select("id", count="exact")
                .eq("lead_id", lead_id)
                .execute()
            )
            return (result.count or 0) > 0
        except Exception:
            return False  # Em caso de erro, não bloqueia

    def get_last_orcamento(self, lead_id: str) -> dict | None:
        """Retorna o último orçamento gerado para o lead."""
        try:
            result = (
                supabase.table("orcamentos")
                .select("*")
                .eq("lead_id", lead_id)
                .order("criado_em", desc=True)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Erro ao buscar último orçamento: {e}")
            return None

    def save_orcamento(
        self,
        lead_id: str,
        itens: list[dict],
        valor_total: float,
        pdf_url: str,
        observacoes: str = "",
    ) -> dict:
        """Salva registro do orçamento gerado."""
        try:
            numero = f"ORC-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
            result = supabase.table("orcamentos").insert({
                "numero": numero,
                "lead_id": lead_id,
                "itens": itens,
                "valor_total": valor_total,
                "pdf_url": pdf_url,
                "status": "enviado",
                "observacoes": observacoes,
                "validade_dias": settings.quote_validity_days,
            }).execute()
            logger.info(f"Orçamento salvo: {numero} | R$ {valor_total:.2f}")
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f"Erro ao salvar orçamento: {e}")
            raise SupabaseError(f"Falha ao salvar orçamento: {e}")


# Instância global
memory = AgentMemory()
