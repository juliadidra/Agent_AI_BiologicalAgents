# Multi-agente in-process (roteador + especialistas)

## Context

Hoje o assistente responde tudo com **uma única chamada de LLM** empacotando RAG + histórico + info de tratamento + perfil no mesmo prompt monolítico (`prompt_template.jinja`, 83 linhas com persona + guardrails + regras de agendamento + RAG misturados). Dois modos conflitam nesse prompt único: (a) responder dúvida clínica ancorada no PCDT e (b) executar ação estruturada de tratamento via tool. Objetivos conflitantes no mesmo prompt diluem os dois.

Objetivo (decidido com a Julia): **roteador + especialistas in-process**, foco em **qualidade das respostas** — não o protocolo A2A formal, não infra nova. Cada agente tem escopo e prompt próprios; um roteador classifica a intenção e despacha. Ao fazer isso, corrigimos dois defeitos abertos que sabotam qualquer melhoria: o loop agêntico não fecha e o `patient_profile` está morto.

## Estado atual (o que reaproveitar)

- `ConversationService.handle_incoming(chat_id, question, history)` — ponto único chamado por `InboxService`. Faz guardrail → fetch profile/treatment → RAG → summarize → prompt → **1 invoke** → despacha **só a 1ª tool** e devolve a string dela **sem realimentar o LLM**. É o orquestrador natural.
- `GroqLLM` (`src/adapters/groq_llm.py`) — `bind_tools` no construtor; `invoke(messages)` passa direto pro `ChatGroq`. Reutilizável para múltiplas instâncias (com/sem tools).
- `GroqGuardrail` — já é um "agente" especialista separado. Padrão a seguir para o roteador.
- `RagPipeline.search(query) -> list[str]`, `LangChainSummarizer.summarize`, `TreatmentService` (schedule/cancel/get_summary), `PatientService.get_profile`, `LOCAL_TOOLS` (as 3 tools) — todos reaproveitados sem mudança de assinatura.
- `PromptBuilder.build(...)` — hoje hardcoda 1 template. Será generalizado para receber nome de template + contexto.

## Arquitetura alvo

```
InboxService.process_message
        │
        ▼
ConversationService.handle_incoming   ← vira ORQUESTRADOR
        │  CAMADA 1 — guardrail.is_safe(question)  → se unsafe, curto-circuita ANTES
        │              de montar contexto/rotear/chamar qualquer agente.
        │  2. monta AgentContext UMA vez:
        │       profile = patient_service.get_profile
        │       treatment_info = treatment_service.get_summary
        │       history_summary = summarizer.summarize
        │  3. route = router.classify(question, context)
        │  4. agent = {TREATMENT|CLINICAL|SUPPORT}[route]   (SUPPORT = default/catch-all)
        ▼
   agent.handle(AgentContext) -> str
   ├─ TreatmentAgent  (LLM + 3 tools, LOOP agêntico real)
   ├─ ClinicalAgent   (RAG lazy + LLM sem tools, ancorado no PCDT)
   └─ SupportAgent    (LLM sem tools, empatia/adesão + trata off-topic via prompt)
```

Off-topic **não** é rota nem resposta fixa: o guardrail (camada 1) barra o que é impróprio/crítico; o resto que fugir do escopo cai em SUPPORT, cujo prompt sabe redirecionar gentilmente sem alimentar a conversa off-topic.

Ganho de latência de brinde: **RAG só roda quando roteia p/ CLINICAL** (hoje roda sempre).

## Componentes

### 1. Contrato e contexto compartilhado
- **`src/ports/agent.py`** (novo) — `Agent` Protocol com `handle(ctx: AgentContext) -> str`; `Router` Protocol com `classify(ctx: AgentContext) -> Route`.
- **`src/services/agent_context.py`** (novo) — `@dataclass AgentContext` (`chat_id, question, today, history_summary, last_turn, patient_profile, treatment_info`) + `Enum Route {TREATMENT, CLINICAL, SUPPORT}`. Montado uma vez pelo orquestrador (que extrai `last_turn` = último par user/assistant do `history` bruto). O router usa `question + history_summary + last_turn + has_active_treatment`; os especialistas usam `history_summary`. SUPPORT é o catch-all (inclui off-topic).

### 2. Roteador — `src/services/agent_router.py` (novo)
- Classificador LLM (modelo barato — ver settings). Devolve **um único** label do enum `Route`.
- **Entrada do router (decisão de design):** sinal primário = `question` (mensagem atual). Contexto secundário complementar (ambos já computados, custo zero): `history_summary` (contexto estabelecido em vários turnos, já destilado pelo summarizer) + `last_turn` (recência/anáfora, que o summary costuma perder — ex.: "o bot acabou de perguntar a data final") + flag `has_active_treatment`. Histórico-só é rejeitado (classificaria o passado); pergunta-só quebra em respostas curtas do fluxo de agendamento ("dia 10", "pode ser", "e a final?"). Risco a mitigar: grudência de tópico → ver regra anti-grudência no prompt.
- Prompt novo `src/prompts/router.jinja`: instruções curtas + **regra anti-grudência** ("priorize a mensagem atual; use o histórico só para resolver referências e respostas curtas") + few-shot de fronteira (ex.: "quero parar de tomar" → TREATMENT; "esse remédio corta o efeito da pílula?" → CLINICAL; "tô com medo de contar pra minha família" → SUPPORT; "qual a capital da França" → SUPPORT, que trata off-topic). Baixa temperatura, parse defensivo com **fallback → SUPPORT** se a saída não casar.
- Espelha o padrão do `GroqGuardrail` (invoke → parse string).

### 3. Especialistas (flat em `services/`, sem tools exceto o de tratamento)
Cada um implementa `Agent.handle(ctx)` e tem prompt próprio (decomposição do jinja monolítico):

- **`src/services/treatment_agent.py`** — LLM **com** as 3 tools. Implementa **loop agêntico real** (corrige o defeito): `invoke → se tool_calls: executa TODAS, anexa AIMessage + ToolMessage(tool_call_id, resultado) → re-invoke → repete até sem tool_calls ou `MAX_TOOL_ITERS` (2–3)` → retorna `content` final. Reaproveita `_dispatch`/`_find_tool` movidos do `ConversationService`. Prompt `src/prompts/treatment.jinja`: só regras de agendamento/cancelamento (seções 3 do jinja atual) + `treatment_info` + `patient_profile`. Usa `langchain_core.messages` (AIMessage/ToolMessage).
- **`src/services/clinical_agent.py`** — RAG **lazy** (`rag_pipeline.search(ctx.question)`), LLM **sem** tools. Prompt `src/prompts/clinical.jinja`: responder ancorado em `{{context}}`, nunca prescrever/diagnosticar, orientar procurar profissional + `patient_profile`.
- **`src/services/support_agent.py`** — LLM sem tools, sem RAG. É o **catch-all** (recebe off-topic). Prompt `src/prompts/support.jinja`: empatia, adesão, continuidade da conversa + `history_summary` + `patient_profile` + `treatment_info`. Regra "não oferecer lembrete repetidamente" (seções 2 e regra anti-encerramento do jinja atual) vive aqui. **Trata off-topic via prompt**: se o assunto fugir do escopo médico-comportamental, redireciona gentilmente para o cuidado do paciente sem alimentar a conversa off-topic — sem resposta hardcoded.

### 4. Prompts — decompor o monolito
- Manter o **bloco de guardrails/segurança** (linhas 5–19 do jinja atual) como parcial compartilhada: `src/prompts/_guardrails.jinja` incluída via `{% include %}` em treatment/clinical/support. Evita divergência de política entre agentes.
- `PromptBuilder` generalizado: `build(template_name, question, **context) -> list[dict]`. Cada agente passa só as vars que usa. **Todos** os templates renderizam `patient_profile` (corrige o dado morto).

### 5. Orquestrador — reescrever `ConversationService`
- Mantém assinatura `handle_incoming(chat_id, question, history)` → **`InboxService` não muda** (compat externa preservada).
- Novo fluxo: **guardrail (camada 1, curto-circuita antes de tudo)** → montar `AgentContext` (uma vez) → `router.classify` → `agents[route].handle(ctx)`. Try/except global mantém `_ERROR_RESPONSE`.
- Recebe no construtor: `guardrail`, `router`, e um `dict[Route, Agent]` (ou os 3 agentes explícitos). Sai: `rag_pipeline`, `prompt_builder`, `llm`, `tool_registry` (migram para dentro dos agentes).

### 6. Wiring — `src/core/container.py` + `src/api/main.py`
- `GroqLLM` **duas instâncias**: `llm_tools = GroqLLM(..., tools=tool_registry.get_tools())` e `llm_plain = GroqLLM(...)` (sem tools).
- Instanciar `AgentRouter`, `TreatmentAgent(llm_tools, tool_registry, prompt_builder, treatment_service)`, `ClinicalAgent(llm_plain, rag_pipeline, prompt_builder)`, `SupportAgent(llm_plain, prompt_builder)`.
- `Container`: adicionar campos `router`, `treatment_agent`, `clinical_agent`, `support_agent`, `llm_plain` (renomear `llm`→`llm_tools`). `conversation_service` passa a receber router + agentes.
- **Settings** (`src/core/settings.py` + `.env.example`): `GROQ_AI_ROUTER_MODEL` (default = `GROQ_AI_GUARDRAILS_MODEL` se ausente).

### 7. Correção acoplada (recomendada) — mensagem duplicada
Hoje `TreatmentService.schedule/cancel` faz `messaging.send(...)` **e** retorna a mesma string, que `InboxService` envia de novo → 2 mensagens. Com o loop agêntico, o `send` interno + a resposta final do LLM continuam gerando 2 envios. **Recomendo remover o `self._messaging.send(...)` de `schedule`/`cancel`** (o serviço volta a fazer só domínio; o único envio passa a ser o turno final do agente via `InboxService`). Requer ajustar os testes existentes do `TreatmentService`.

## Arquivos

Novos: `src/ports/agent.py`, `src/services/agent_context.py`, `src/services/agent_router.py`, `src/services/treatment_agent.py`, `src/services/clinical_agent.py`, `src/services/support_agent.py`, `src/prompts/{router,treatment,clinical,support,_guardrails}.jinja`.

Modificados: `src/services/conversation_service.py` (reescrita p/ orquestrador), `src/services/prompt_builder.py` (generalizar), `src/services/treatment_service.py` (remover send — item 7), `src/core/container.py`, `src/core/settings.py`, `src/api/main.py`, `.env.example`. `prompt_template.jinja` fica obsoleto (remover após migração).

Inalterados (compat): `src/api/routes/*`, `src/api/dto.py`, `src/services/inbox_service.py`, `src/tools/langchain_tools.py`, `src/adapters/*` (exceto reuso de `GroqLLM`).

## Testes (unit, mockando LLM/RAG/repos — segue `tests/` atual)
- `agent_router`: cada label é retornado; saída inválida/off-topic → fallback SUPPORT.
- `treatment_agent`: loop executa tool, realimenta resultado, retorna content final; respeita `MAX_TOOL_ITERS`.
- `clinical_agent`: chama `rag_pipeline.search` e injeta docs; sem tools.
- `support_agent`: responde sem RAG/tools; mensagem off-topic → resposta gerada pelo LLM que redireciona (não string fixa).
- `conversation_service` (orquestrador): despacha para o agente certo por `Route`; guardrail unsafe curto-circuita; off-topic vai para SUPPORT.
- Ajustar testes de `treatment_service` para o item 7.

## Verificação end-to-end
1. `pytest` verde (novos + ajustados).
2. Subir local (`docker-compose up` ou uvicorn) e `POST /agent/webhook` com payloads WAHA simulando cada rota:
   - "esse remédio corta o efeito de outros?" → resposta ancorada em RAG (CLINICAL).
   - "quero agendar lembrete do Tenofovir a partir de hoje" → tool dispara, **um** ✅ chega, resposta final natural (TREATMENT + loop).
   - "tô com medo dos efeitos" → acolhimento sem oferta de lembrete (SUPPORT).
   - "qual a capital da França" → SUPPORT redireciona gentilmente ao escopo, sem alimentar o off-topic (resposta do LLM, não fixa).
   - mensagem imprópria/injeção → barrada na camada 1 (guardrail), sem chegar em router/agente.
3. Conferir nos logs que RAG **não** roda em turnos TREATMENT/SUPPORT.

## Fora de escopo
- Protocolo A2A formal / agentes como serviços separados (decidido: in-process).
- MCP (`fastmcp` já está no requirements, mas `ToolRegistry.providers` fica como hook futuro).
- Memória de perfil de paciente rica (`ensure_profile_exists` continua sem uso; apenas passamos a **renderizar** o profile existente).
