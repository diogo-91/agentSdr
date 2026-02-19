# 🤖 SDR Agent — Ana Laura
**Agente de vendas SDR automatizado para WhatsApp**  
Empresas de telhas, portas metálicas e acessórios.

> [!IMPORTANT]
> Nunca suba o arquivo `credentials.json` ou o `.env` no GitHub!

---

## 🏗️ Arquitetura

```
Cliente WhatsApp → Evolution API → Webhook FastAPI → Agente (Grok AI)
                                                           ↓
                                     Memória (Supabase) ← → Google Sheets
                                                           ↓
                                     PDF Orçamento → Supabase Storage → WhatsApp
                                                           ↓
                                                    Gestor de Vendas
```

---

## ⚙️ Configuração

### 1. Clone e configure
```bash
git clone https://github.com/seu-usuario/sdr-agent.git
cd sdr-agent
cp .env.example .env
# Edite o .env com suas credenciais
```

### 2. Credenciais Google Sheets
1. Acesse [Google Cloud Console](https://console.cloud.google.com)
2. Crie um projeto → Ative **Google Sheets API** e **Google Drive API**
3. Crie uma **Service Account** → Baixe o JSON → salve como `credentials.json` na raiz
4. Compartilhe a planilha com o e-mail da service account

### 3. Supabase — Configure o banco
Execute o script SQL no **SQL Editor** do Supabase:
```
sql/schema.sql
```
Depois, crie o bucket de storage:
- Supabase → Storage → New Bucket → Nome: `orcamentos` → **Public**

---

## 🚀 Deploy no EasyPanel

### Opção A — Via GitHub (Recomendado)
1. No EasyPanel, crie uma **App** → Source: GitHub → selecione o repositório
2. Build Method: **Dockerfile**
3. Porta: `8000`
4. Adicione todas as variáveis do `.env.example` nas **Environment Variables**
5. Monte o arquivo `credentials.json` como um arquivo de secrets ou variável base64

### Opção B — Docker Compose (VPS direto)
```bash
docker-compose up -d --build
```

---

## 🔗 Configurar Webhook no Evolution API

Após subir a aplicação, configure o webhook da sua instância Evolution:

- **URL:** `https://seu-dominio.com/webhook`
- **Eventos:** `messages.upsert`
- **Autenticação:** não necessária (use Cloudflare ou proxy para segurança)

---

## 📁 Estrutura do Projeto

```
sdr-agent/
├── api/              # FastAPI (webhook + main)
├── agent/            # Orquestrador + persona + memória + tools
├── integrations/     # Grok AI, Google Sheets, Evolution API
├── pdf/              # Gerador de PDF + template HTML
├── db/               # Cliente Supabase
├── core/             # Config, logger, exceptions
├── sql/              # Schema do banco de dados
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## 🧪 Teste Local

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar servidor
uvicorn api.main:app --reload --port 8000

# Em outro terminal, use ngrok para expor:
ngrok http 8000
# Configure a URL ngrok no webhook do Evolution API
```

---

## 📊 Banco de Dados (Supabase)

| Tabela | Descrição |
|---|---|
| `leads` | Clientes cadastrados |
| `messages` | Histórico de conversas (memória) |
| `orcamentos` | Orçamentos gerados com PDF |

---

## 🔐 Variáveis de Ambiente

| Variável | Descrição |
|---|---|
| `GROK_API_KEY` | Chave da API xAI/Grok |
| `SUPABASE_URL` | URL do projeto Supabase |
| `SUPABASE_SERVICE_KEY` | Service Role Key do Supabase |
| `GOOGLE_SHEETS_ID` | ID da planilha de preços |
| `GOOGLE_CREDENTIALS_PATH` | Caminho para o credentials.json |
| `EVOLUTION_API_URL` | URL da Evolution API |
| `EVOLUTION_API_KEY` | API Key da Evolution |
| `EVOLUTION_INSTANCE` | Nome da instância |
| `MANAGER_PHONE` | Telefone do gestor (5511999999999) |
| `AGENT_NAME` | Nome do SDR (ex: Ana Laura) |
| `COMPANY_NAME` | Nome da empresa |

---

## 🩺 Health Check

```
GET /health
```
Retorna status do agente. Usado pelo Docker e EasyPanel para monitoramento.
