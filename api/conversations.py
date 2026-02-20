"""
Endpoints para visualização de conversas e leads.
GET /conversations          → lista todos os leads
GET /conversations/{lead_id} → histórico completo de mensagens de um lead
"""
from fastapi import APIRouter, HTTPException
from db.supabase_client import supabase
from core.logger import logger

router = APIRouter(prefix="/conversations", tags=["Conversas"])


@router.get("")
def list_leads():
    """Lista todos os leads com status e última mensagem."""
    try:
        result = (
            supabase.table("leads")
            .select("id, nome, telefone, status, criado_em")
            .order("criado_em", desc=True)
            .execute()
        )
        leads = result.data or []

        # Para cada lead, busca a última mensagem
        for lead in leads:
            last_msg_result = (
                supabase.table("messages")
                .select("role, content, criado_em")
                .eq("lead_id", lead["id"])
                .order("criado_em", desc=True)
                .limit(1)
                .execute()
            )
            if last_msg_result.data:
                lead["ultima_mensagem"] = last_msg_result.data[0]
            else:
                lead["ultima_mensagem"] = None

        return {"total": len(leads), "leads": leads}

    except Exception as e:
        logger.error(f"Erro ao listar leads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{lead_id}")
def get_conversation(lead_id: str):
    """Retorna lead + histórico completo de mensagens."""
    try:
        # Busca o lead
        lead_result = (
            supabase.table("leads")
            .select("*")
            .eq("id", lead_id)
            .execute()
        )
        if not lead_result.data:
            raise HTTPException(status_code=404, detail="Lead não encontrado.")

        lead = lead_result.data[0]

        # Busca todas as mensagens
        messages_result = (
            supabase.table("messages")
            .select("role, content, criado_em")
            .eq("lead_id", lead_id)
            .order("criado_em", desc=False)
            .execute()
        )

        # Busca orçamentos
        orcamentos_result = (
            supabase.table("orcamentos")
            .select("valor_total, pdf_url, criado_em")
            .eq("lead_id", lead_id)
            .order("criado_em", desc=False)
            .execute()
        )

        return {
            "lead": lead,
            "mensagens": messages_result.data or [],
            "orcamentos": orcamentos_result.data or [],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar conversa {lead_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
