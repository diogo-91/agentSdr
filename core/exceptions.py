"""
Exceções customizadas para tratamento de erros claro e descritivo.
"""


class SDRAgentError(Exception):
    """Base exception para o SDR Agent."""
    pass


class GrokAPIError(SDRAgentError):
    """Erro na comunicação com a Grok API."""
    pass


class EvolutionAPIError(SDRAgentError):
    """Erro na comunicação com a Evolution API."""
    pass


class GoogleSheetsError(SDRAgentError):
    """Erro ao acessar o Google Sheets."""
    pass


class SupabaseError(SDRAgentError):
    """Erro ao acessar o Supabase."""
    pass


class PDFGenerationError(SDRAgentError):
    """Erro na geração do PDF."""
    pass


class LeadNotFoundError(SDRAgentError):
    """Lead não encontrado no banco de dados."""
    pass
