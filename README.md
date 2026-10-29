# Biological Agents — Assistente de WhatsApp para PEP

Agente de IA que atende pelo WhatsApp e orienta pacientes sobre a **Profilaxia Pós-Exposição (PEP)** ao HIV. Ele responde dúvidas com base no PCDT oficial (RAG), dá apoio emocional e gerencia lembretes diários de medicação.

## Funcionalidades

- **Respostas fundamentadas (RAG):** busca no PCDT no Chroma, com reranking pela Cohere.
- **Lembretes de medicação:** agenda e cancela tratamentos e envia lembretes diários, com os dados no Firestore.
- **Guardrails:** um modelo classifica cada mensagem como `SAFE` ou `UNSAFE` (prompt injection e conteúdo nocivo) antes do agente responder.
- **Memória de conversa:** resume o histórico para manter o contexto.
- **Mensagem de boas-vindas** no primeiro contato.

## Arquitetura

```
WhatsApp ──► WAHA ──► POST /agent/webhook ──► FastAPI
                                                │
                       ┌────────────────────────┼─────────────────────┐
                       ▼                        ▼                     ▼
                Guardrails (Groq)      Agente LLM (Groq)       Tools (Firestore)
                                              │                 - schedule/cancel treatment
                                              ▼                 - get_user_information
                                  RAG: Chroma Cloud + embeddings
                                  locais (all-MiniLM-L6-v2) + Cohere rerank
```

| Camada | Tecnologia |
|---|---|
| API | FastAPI + Uvicorn |
| LLM / guardrails | Groq (via LangChain) |
| Gateway WhatsApp | [WAHA](https://waha.devlike.pro/) |
| Vector store | Chroma Cloud |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` (CPU, local) |
| Reranker | Cohere |
| Banco | Firebase Firestore |
| Prompts | Jinja2 (`prompts/`) |

## Estrutura

```
app.py                      # FastAPI: webhook e lembretes diários
config/settings.py          # leitura das variáveis de ambiente
services/groq_ai/           # agente, prompt e guardrails
services/rag/               # busca vetorial + rerank (e PDF do PCDT)
services/waha/              # cliente da API do WAHA
tools/                      # tools do agente (lembretes, dados do usuário)
prompts/                    # template do prompt e mensagem padrão
helpers/                    # utilitários do WAHA
```

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| POST | `/agent/webhook` | Recebe as mensagens do WAHA e responde ao usuário |
| POST | `/agent/daily-reminders` | Dispara os lembretes diários de medicação |

## Configuração

Crie um `.env` na raiz:

```env
# Groq (LLM principal e guardrail)
GROQ_API_KEY=
GROQ_AI_MODEL=qwen/qwen3-32b
GROQ_AI_GUARDRAILS_MODEL=

# WAHA
WAHA_URL=http://waha:3000
WAHA_API_KEY=

# Chroma Cloud
CHROMA_API_KEY=
CHROMA_TENANT_ID=
CHROMA_DATABASE=

# Cohere (reranker)
COHERE_API_KEY=

# HuggingFace (opcional)
HUGGINGFACE_API_KEY=

# CORS: lista JSON de origens
ALLOW_ORIGINS=["http://localhost:3000"]

# Firebase: JSON ou base64 do JSON da service account
# (alternativa: arquivo firebase-credentials.json na raiz)
FIREBASE_CREDENTIALS=
```

> Nunca versione o `.env` nem o `firebase-credentials.json`.

## Como rodar

Requisitos: Docker e Docker Compose.

```bash
docker compose up --build waha   # WhatsApp gateway (porta 3000)
docker compose up --build api    # API (porta 8000)
```

1. Abra o dashboard do WAHA em `http://localhost:3000` e conecte a sessão do WhatsApp (QR code).
2. Configure o webhook da sessão para `http://api:8000/agent/webhook/` (ou o IP do host, em execução local).
3. Agende uma chamada diária (cron) para `POST /agent/daily-reminders`.

## Aviso

O assistente tem caráter informativo e de apoio. Ele não substitui atendimento médico nem o serviço de saúde.
