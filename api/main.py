"""
Ponto de entrada principal da aplicação FastAPI.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.logger import logger
from api.webhook import router as webhook_router

# Cria pasta de logs se não existir
os.makedirs("logs", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida da aplicação."""
    logger.info("=" * 60)
    logger.info(f"🤖 SDR Agent '{settings.agent_name}' iniciando...")
    logger.info(f"🏢 Empresa: {settings.company_name}")
    logger.info(f"🌐 Evolution Instance: {settings.evolution_instance}")
    logger.info("=" * 60)

    # Valida conexão com Supabase na inicialização
    try:
        from db.supabase_client import supabase
        supabase.table("leads").select("id").limit(1).execute()
        logger.info("✅ Conexão Supabase: OK")
    except Exception as e:
        logger.warning(f"⚠️  Supabase não disponível na inicialização: {e}")

    # Pré-carrega planilha no cache
    try:
        from integrations.sheets_client import sheets_client
        products = sheets_client.get_all_products()
        logger.info(f"✅ Google Sheets: {len(products)} produtos carregados")
    except Exception as e:
        logger.warning(f"⚠️  Google Sheets não disponível na inicialização: {e}")

    logger.info(f"🚀 API pronta na porta {settings.port}")
    yield
    logger.info("SDR Agent encerrado.")


app = FastAPI(
    title=f"SDR Agent — {settings.agent_name}",
    description="Agente SDR automatizado para WhatsApp",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router, tags=["Webhook"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=False,
        log_level="info",
    )
