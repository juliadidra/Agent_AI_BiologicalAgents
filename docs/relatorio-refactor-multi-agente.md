# Relatório — Refatoração para Orquestrador Único + Tools

> Migração de um assistente de **uma única chamada de LLM com prompt monolítico** para um **orquestrador único movido a tools** (loop agêntico real). Este documento percorre cada arquivo de produção alterado ou criado, explicando **o que** foi feito e **por quê**. Arquivos de teste ficam de fora (a pedido).

> **Nota histórica:** durante a evolução chegamos a projetar uma arquitetura multi-agente (roteador + especialistas TREATMENT/CLINICAL/SUPPORT, depois um supervisor dinâmico). Essa linha foi **descartada** por over-engineering para um bot de WhatsApp sensível a latência (chegou a gerar `429` por excesso de chamadas de LLM aninhadas). A decisão final foi **colapsar tudo em um único orquestrador cujas "especialidades" viraram tools que retornam dados**. O critério que fechou a escolha: *"faz (tool) vs decide (agente)"* — como os especialistas só precisavam devolver dados ao orquestrador, eram tools disfarçadas.

## Sumário da mudança

Antes, `ConversationService` fazia tudo numa tacada: guardrail → busca de perfil/tratamento → RAG → resumo → **um** prompt gigante (`prompt_template.jinja`) → **um** `invoke` → despachava **só a primeira tool** e devolvia a string dela **sem realimentar o LLM**. Dois modos conflitavam no mesmo prompt: responder dúvida clínica ancorada no protocolo **e** executar ação de tratamento via tool.

Depois, o fluxo virou uma orquestração enxuta com **um só LLM**:

```
guardrail (camada 1, curto-circuita)
        │
        ▼
monta AgentContext (1x)
        │
        ▼
OrchestratorAgent.handle(ctx)
        │  loop agêntico:
        │    invoke → tem tool_calls?
        │      não → retorna content final (com guard de vazio)
        │      sim → executa TODAS, realimenta ToolMessage → re-invoke
        │            até sem tool_calls ou MAX_TOOL_ITERS (4)
        ▼
     resposta ao paciente
```

Três defeitos abertos foram corrigidos de brinde:
1. **Loop agêntico quebrado** — o resultado da tool não voltava pro LLM. Agora o orquestrador realimenta via `ToolMessage`.
2. **`patient_profile` morto** — era buscado mas nunca renderizado (e nunca escrito). Agora o prompt do orquestrador o recebe **e** o modelo pode alimentá-lo via tool (ver "Perfil do paciente" abaixo).
3. **Mensagem duplicada** — `TreatmentService` mandava a mensagem *e* devolvia a string, gerando dois envios. O envio interno saiu.

---

## Arquivos de contexto e contrato (novos)

### `src/ports/agent.py` (novo)
Define o **contrato** `Agent` como `Protocol`: exige `handle(ctx: AgentContext) -> str`.

**Por quê:** o `ConversationService` depende do *contrato*, não da classe concreta `OrchestratorAgent` — despacha para qualquer objeto que tenha `handle`. Facilita testes com fakes (`FakeAgent`). Usa `TYPE_CHECKING` + `from __future__ import annotations` para referenciar `AgentContext` sem import circular. O antigo `Router` Protocol foi **removido** (não há mais roteador).

### `src/services/agent_context.py` (novo)
- **`AgentContext`** — `@dataclass` com tudo que o orquestrador precisa: `chat_id`, `question`, `today`, `history_summary`, `last_turn`, `patient_profile`, `treatment_info`. Tem a `@property has_active_treatment`, que lê `treatment_info`.
- **`extract_content(response)`** — helper que puxa `.content` de uma resposta de LLM de forma defensiva (trata não-string) e passa por `strip_reasoning`.

**Por quê:** o contexto é montado **uma única vez** pelo orquestrador e passado adiante — evita refazer buscas. Centralizar `extract_content` evita repetir boilerplate defensivo.

### `src/core/text.py` (novo)
`strip_reasoning(text)` — remove blocos `<think>...</think>` que modelos de reasoning (qwen3, deepseek-r1) emitem dentro do `content`. Estratégia: corta tudo até o **último** `</think>` e limpa pares residuais com regex.

**Por quê:** o `<think>` vazava na resposta ao paciente e contaminava a **checagem do guardrail** e o **resumo** (que alimenta o orquestrador). Fica em `core/` — local neutro — para que **adapters** possam importar sem depender de `services/`.

---

## Orquestrador e tools

### `src/services/orchestrator_agent.py` (novo)
O **agente único** movido a tools. Um LLM (`llama-3.3-70b-versatile`, não-reasoning) raciocina sobre a mensagem, consulta ferramentas que devolvem **dados** e escreve a resposta final. Implementa o **loop agêntico real** (`MAX_TOOL_ITERS = 4`):

```
invoke → tem tool_calls?
  não → _finalize(response)  → content, ou _EMPTY_FALLBACK se vazio
  sim → executa TODAS, anexa a AIMessage + ToolMessage(tool_call_id, resultado) → re-invoke
```

- `_execute_tool` acha a tool no registry pelo `.name`, faz parse defensivo dos args (JSON string → dict), invoca com `try/except` (cada erro vira mensagem factual pro LLM, não estoura).
- `_finalize` aplica o **guard de vazio**: se o content final for vazio (modelo pediu tool e nunca redigiu), devolve `_EMPTY_FALLBACK` em vez de mandar mensagem em branco.

**Por quê:** corrige o defeito central do fluxo antigo — o resultado da tool **volta** pro LLM, então o modelo redige a confirmação com base no que a ferramenta de fato retornou. Um único LLM elimina os loops aninhados que causavam `429`. Modelo **não-reasoning** foi escolhido porque os de reasoning (qwen3) devolviam `content` vazio dentro do loop de tool-calling.

### `src/tools/langchain_tools.py` (modificado — RAG virou tool)
Além das 3 tools de tratamento (`schedule_medication_treatment`, `cancel_medication_treatment`, `get_user_information`), foi adicionada `search_clinical_knowledge(query)`: busca no material clínico (PCDT) via `rag_pipeline.search`, com tratamento de "nada encontrado" e de exceção. Todas entram em `LOCAL_TOOLS`.

**Por quê:** o RAG deixou de ser **sempre injetado** no prompt (custo em todo turno) e virou uma **tool lazy** — só busca quando o orquestrador decide que a dúvida é clínica. Ganho de latência nos turnos que não são clínicos.

---

## Prompt — um só, decomposto do monolito

O `prompt_template.jinja` (83 linhas misturando persona + guardrails + regras + RAG) foi **removido**. As regras foram concentradas num único prompt de orquestrador.

### `src/prompts/orchestrator.jinja` (novo)
O prompt unificado do orquestrador. Contém, num só lugar:
- **Persona** + inclusão do parcial `{% include "_guardrails.jinja" %}`.
- **Dúvidas clínicas:** regra de **chamar `search_clinical_knowledge` SEMPRE antes** de responder sobre medicação/efeitos/protocolo, e responder **somente** com base no que a busca retornar (nada de resposta vaga tipo "parece que...").
- **Lembretes de medicação:** dados necessários para agendar + **reuso de informação já conhecida** (não repergunta o que o paciente já disse; ex.: se já citou que trata HIV, pergunta só as datas que faltam) + trava de que o `{{ chat_id }}` já é conhecido pelo sistema (**nunca** pedir ao paciente).
- **Trava de fidelidade:** após uma tool executar, confirmar usando **exatamente** os dados retornados — nunca inventar/alterar datas, medicamento ou status.
- **Apoio/conversa:** empatia, continuidade, regra "não oferecer lembrete repetidamente", anti-encerramento forçado, e redirecionamento de off-topic via prompt.
- **Primeira interação:** bloco `{% if not history_summary %}` que cumprimenta e apresenta a capacidade de lembretes só no primeiro contato.
- Renderiza `treatment_info`, `patient_profile` e `history_summary`.

### `src/prompts/_guardrails.jinja` (novo)
O bloco de segurança/limitações extraído do monolito, incluído via `{% include %}` no orquestrador.

**Por quê:** política de segurança num lugar só. É a instrução de segurança *dentro* do prompt; distinta do `GroqGuardrail` (camada 1), que é uma checagem separada antes de tudo.

---

## Orquestração e serviços (modificados)

### `src/services/conversation_service.py` (reescrito → orquestrador)
- **Construtor:** `guardrail`, `orchestrator`, `patient_service`, `treatment_service`, `summarizer`.
- **`handle_incoming(chat_id, question, history)`** mantém a assinatura — **`InboxService` não muda** (compatibilidade externa preservada).
- **Fluxo:** guardrail (camada 1, curto-circuita com `UNSAFE_RESPONSE` **antes** de montar contexto) → `_build_context` → `self._orchestrator.handle(ctx)`, dentro de `try/except` global que devolve `_ERROR_RESPONSE`.
- **`_build_context`** monta o `AgentContext` uma vez. `_summarize_history` normaliza o histórico bruto do WhatsApp (`fromMe`/`body`) e resume com `try/except` (falha → resumo vazio). `_extract_last_turn` pega as últimas até 2 mensagens não vazias.

**Por quê:** o serviço "coordena" em vez de "fazer": guardrail como primeira camada, contexto montado uma vez, e delegação ao orquestrador. Toda a lógica de resposta mora no agente.

### `src/services/prompt_builder.py` (generalizado)
`build(template_name, question, **context)` renderiza **qualquer** template como mensagem de sistema e devolve `[system, user]`. Registra o filtro Jinja `json_pt` (`json.dumps(..., ensure_ascii=False)`) para serializar dicts preservando acentos.

**Por quê:** deixou de hardcodar um único template; hoje serve o `orchestrator.jinja`. O `ensure_ascii=False` evita `\uXXXX` no prompt.

### `src/services/treatment_service.py` (modificado — sem envio de mensagem)
- **Removida a dependência de `messaging`** — recebe só `treatment_repository`.
- `schedule`/`cancel` devolvem **strings factuais de status** (medicamento, datas, status) em vez de mandar mensagem.

**Por quê:** o envio interno + a string retornada geravam **mensagem duplicada**. Agora o serviço só faz domínio e devolve o fato; quem envia é o turno final do orquestrador via `InboxService`. Essa string factual é a fonte da verdade que o orquestrador realimenta no LLM.

### `src/adapters/groq_guardrail.py` (modificado)
Aplica `strip_reasoning(content)` antes de checar `"UNSAFE"`. Loga e devolve `True` (fail-open) se o content não for string.

**Por quê:** sem o strip, um "não é UNSAFE" dentro de um `<think>` bloquearia mensagens legítimas por engano.

### `src/adapters/langchain_summarizer.py` (modificado)
Passa o resultado de `predict_new_summary` por `strip_reasoning`.

**Por quê:** o resumo alimenta o orquestrador; um `<think>` vazado poluiria esse contexto.

### `src/adapters/groq_llm.py` (modificado)
No construtor, liga as tools ao cliente via `chat.bind_tools(tools)` (do LangChain) quando `tools` é passado; senão usa o `ChatGroq` cru. `invoke` delega para o runnable resultante.

**Por quê:** o wiring monta a instância já com as tools (`GroqLLM(..., tools=...)`), num único lugar. Um método `bind_tools` público e a declaração correspondente no `LLMProvider` Protocol chegaram a existir na fase do supervisor (binding por-request) e foram **removidos** por não terem consumidor.

---

## Configuração e wiring (modificados)

### `src/core/settings.py` (modificado)
- `GROQ_AI_TOOLS_MODEL: str | None = None` — modelo do orquestrador (tool-calling, não-reasoning). Se ausente, cai em `GROQ_AI_MODEL`.

### `src/core/container.py` (modificado)
A **caixa** (dataclass) perdeu os slots da fase multi-agente (`llm_plain`, `llm_router`, `router`, `treatment_agent`, `clinical_agent`, `support_agent`, `supervisor`) e ganhou `orchestrator`. Mantém `llm_tools`.

### `src/api/main.py` (modificado — composition root)
No `_build_container`:
- Resolve o modelo do orquestrador com fallback simples:
  ```python
  tools_model = settings.GROQ_AI_TOOLS_MODEL or settings.GROQ_AI_MODEL
  ```
- `llm_tools = GroqLLM(..., model=tools_model, tools=tool_registry.get_tools())`.
- Instancia `OrchestratorAgent(llm=llm_tools, tool_registry, prompt_builder)`.
- `ConversationService` com a assinatura nova; `TreatmentService` sem `messaging`.
- **Modelos por papel:** orquestrador → `tools_model`; guardrail → `GROQ_AI_GUARDRAILS_MODEL`; summarizer → `GROQ_AI_MODEL`.

**Por quê:** único ponto onde a aplicação é montada (composition root). A cadeia de fallback deixa o orquestrador funcionar mesmo com a env legada `GROQ_AI_ROUTER_MODEL` ainda preenchida.

### `.env.example` (modificado)
Reflete as envs de modelo por papel.

---

## Endpoint de teste (novo)

### `src/api/routes/sandbox.py` (novo)
`POST /agent/test-message` — injeta uma mensagem direto no fluxo do agente e devolve a resposta no corpo HTTP, **sem WAHA/WhatsApp**. Chama `conversation.handle_incoming` via `run_in_threadpool` (código síncrono/lento fora do event loop).

**Por quê:** permite testar o orquestrador (clínico/tratamento/apoio/off-topic/injeção) sem subir a infra de WhatsApp. O arquivo se chama `sandbox.py` (e não `test_message.py`) de propósito: `test_*` seria coletado pelo pytest e quebraria a suíte.

---

## Removidos
- `src/prompts/prompt_template.jinja` — substituído pelo `orchestrator.jinja`.
- `src/api/routes/test_message.py` — renomeado para `sandbox.py` (colisão com o pytest).
- Arquivos da fase multi-agente que **não** chegaram a ficar (roteador, especialistas, supervisor e seus prompts/testes) — colapsados no orquestrador único.

## Compatibilidade preservada (inalterados)
`InboxService`, `dto.py`, demais adapters e rotas seguem sem mudança de assinatura — a refatoração é interna ao fluxo de conversa.

## Dívidas conhecidas / próximos passos
- Avaliar modelo mais leve para guardrail/summarizer (ex.: `llama-3.1-8b-instant`).
- O reuso de informação depende do **summarizer** reter detalhes de medicamento/tratamento no `history_summary` — pode exigir ajuste no prompt do resumo.
