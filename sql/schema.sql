-- ============================================================
-- SDR AGENT - Schema SQL para Supabase
-- Execute este script no SQL Editor do Supabase
-- ============================================================

-- Extensão para UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABELA: leads
-- ============================================================
CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telefone TEXT UNIQUE NOT NULL,
    nome TEXT,
    cidade TEXT,
    status TEXT DEFAULT 'novo' CHECK (status IN ('novo', 'qualificando', 'orcamento_enviado', 'negociando', 'fechado', 'perdido')),
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABELA: messages
-- (Memória persistente do agente — histórico completo)
-- ============================================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
    content TEXT NOT NULL,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABELA: orcamentos
-- ============================================================
CREATE TABLE IF NOT EXISTS orcamentos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    numero TEXT UNIQUE NOT NULL,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    itens JSONB NOT NULL DEFAULT '[]'::jsonb,
    subtotal DECIMAL(10, 2) NOT NULL DEFAULT 0,
    desconto DECIMAL(10, 2) DEFAULT 0,
    valor_total DECIMAL(10, 2) NOT NULL DEFAULT 0,
    validade_dias INTEGER DEFAULT 7,
    pdf_url TEXT,
    status TEXT DEFAULT 'enviado' CHECK (status IN ('rascunho', 'enviado', 'aprovado', 'recusado', 'expirado')),
    observacoes TEXT,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TRIGGERS: atualiza updated_at automaticamente
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_leads_updated_at
    BEFORE UPDATE ON leads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orcamentos_updated_at
    BEFORE UPDATE ON orcamentos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- ÍNDICES para performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_leads_telefone ON leads(telefone);
CREATE INDEX IF NOT EXISTS idx_messages_lead_id ON messages(lead_id);
CREATE INDEX IF NOT EXISTS idx_messages_criado_em ON messages(criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_orcamentos_lead_id ON orcamentos(lead_id);
CREATE INDEX IF NOT EXISTS idx_orcamentos_numero ON orcamentos(numero);

-- ============================================================
-- STORAGE BUCKET para PDFs
-- Execute separadamente se necessário
-- ============================================================
-- INSERT INTO storage.buckets (id, name, public)
-- VALUES ('orcamentos', 'orcamentos', true)
-- ON CONFLICT (id) DO NOTHING;
