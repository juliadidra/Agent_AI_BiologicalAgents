## Informacoes importantes
```markdown
## Informacoes importantes
- Url configurada no webhook: http://api:8000/agent/webhook/
- Url configurada no webhook (local): http://172.20.176.1:8000/agent/webhook/
- comando para rodar o waha: docker compose up --build waha
- comando para rodar a api: docker compose up --build api

HUGGINGFACE_API_KEY=
GROQ_API_KEY=
GROQ_AI_MODEL=llama-3.3-70b-versatile
WAHA_URL=http://waha:3000

## Scheduler (lembretes diários)

O projeto inclui um serviço `scheduler` que roda o job de envio de lembretes diário. Ele usa o arquivo
`services/scheduler/run_daily_cron.py` que por sua vez executa `services/scheduler/send_daily_reminders.py`.

Como configurar e executar com Docker Compose:

- Edite `docker-compose.yaml` ou exporte a variável de ambiente `SCHEDULE_TIME` no formato `HH:MM` (24h).
	Exemplo: `SCHEDULE_TIME=09:00` (padrão).
- O serviço `scheduler` depende dos serviços `waha` e `api` para que as chamadas a outros serviços funcionem.
- Para subir tudo com o scheduler:

```powershell
docker compose up --build waha api scheduler
```

Observação: o container do scheduler monta `firebase-credentials.json` como somente leitura; verifique
que o arquivo existe e contém as credenciais corretas para acesso ao Firestore.

```
