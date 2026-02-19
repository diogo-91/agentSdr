"""
Cliente Supabase centralizado com retry e tratamento de erros.
"""
from supabase import create_client, Client
from core.config import settings
from core.logger import logger
from core.exceptions import SupabaseError


def get_supabase_client() -> Client:
    """Retorna cliente Supabase configurado."""
    try:
        client = create_client(
            settings.supabase_url,
            settings.supabase_service_key,
        )
        return client
    except Exception as e:
        logger.error(f"Erro ao criar cliente Supabase: {e}")
        raise SupabaseError(f"Falha ao conectar Supabase: {e}")


# Instância global reutilizável
supabase: Client = get_supabase_client()
