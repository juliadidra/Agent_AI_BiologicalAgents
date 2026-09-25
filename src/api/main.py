import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.adapters.chroma_vector_retriever import ChromaVectorRetriever
from src.adapters.cohere_reranker import CohereReranker
from src.adapters.firestore_patient_repository import FirestorePatientRepository
from src.adapters.firestore_treatment_repository import FirestoreTreatmentRepository
from src.adapters.groq_guardrail import GroqGuardrail
from src.adapters.groq_llm import GroqLLM
from src.adapters.hf_embedder import HFEmbedder
from src.adapters.langchain_summarizer import LangChainSummarizer
from src.adapters.waha_messaging import WahaMessaging
from src.core.container import Container
from src.core.firebase import initialize_firebase
from src.core.logging import setup_logging
from src.core.settings import Settings, get_settings
from src.api.routes import reminders as reminders_route
from src.api.routes import sandbox as sandbox_route
from src.api.routes import webhook as webhook_route
from src.prompts.guardrail_policy import GUARDRAIL_POLICY
from src.services.conversation_service import ConversationService
from src.services.inbox_service import InboxService
from src.services.orchestrator_agent import OrchestratorAgent
from src.services.patient_service import PatientService
from src.services.prompt_builder import PromptBuilder
from src.services.rag_pipeline import RagPipeline
from src.services.reminder_service import ReminderService
from src.services.tool_registry import ToolRegistry
from src.services.treatment_service import TreatmentService
from src.tools.langchain_tools import LOCAL_TOOLS

logger = logging.getLogger(__name__)


def _build_container(settings: Settings) -> Container:
    firestore_client = initialize_firebase()

    messaging = WahaMessaging(
        base_url=settings.WAHA_URL,
        api_key=settings.WAHA_API_KEY,
        session=settings.WAHA_SESSION,
    )
    embedder = HFEmbedder()
    vector_retriever = ChromaVectorRetriever(
        api_key=settings.CHROMA_API_KEY,
        tenant=settings.CHROMA_TENANT_ID,
        database=settings.CHROMA_DATABASE,
        collection_name=settings.CHROMA_COLLECTION_NAME,
    )
    reranker = CohereReranker(api_key=settings.COHERE_API_KEY)
    treatment_repository = FirestoreTreatmentRepository(firestore=firestore_client)
    patient_repository = FirestorePatientRepository(firestore=firestore_client)

    tool_registry = ToolRegistry(local_tools=LOCAL_TOOLS)
    # Orquestrador faz tool-calling: usa um modelo bom em tools (não-reasoning).
    tools_model = settings.GROQ_AI_TOOLS_MODEL or settings.GROQ_AI_MODEL
    llm_tools = GroqLLM(
        api_key=settings.GROQ_API_KEY,
        model=tools_model,
        tools=tool_registry.get_tools(),
    )
    guardrail = GroqGuardrail(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_AI_GUARDRAILS_MODEL,
        policy=GUARDRAIL_POLICY,
    )
    summarizer = LangChainSummarizer(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_AI_MODEL,
    )

    rag_pipeline = RagPipeline(
        embedder=embedder,
        retriever=vector_retriever,
        reranker=reranker,
    )
    prompt_builder = PromptBuilder()
    treatment_service = TreatmentService(
        treatment_repository=treatment_repository,
    )
    patient_service = PatientService(patient_repository=patient_repository)
    reminder_service = ReminderService(
        treatment_repository=treatment_repository,
        messaging=messaging,
    )

    orchestrator = OrchestratorAgent(
        llm=llm_tools,
        tool_registry=tool_registry,
        prompt_builder=prompt_builder,
    )

    conversation_service = ConversationService(
        guardrail=guardrail,
        orchestrator=orchestrator,
        patient_service=patient_service,
        treatment_service=treatment_service,
        summarizer=summarizer,
    )
    inbox_service = InboxService(
        conversation_service=conversation_service,
        messaging=messaging,
        history_limit=settings.HISTORY_MESSAGES_LIMIT,
    )

    return Container(
        settings=settings,
        firestore=firestore_client,
        messaging=messaging,
        llm_tools=llm_tools,
        guardrail=guardrail,
        embedder=embedder,
        vector_retriever=vector_retriever,
        reranker=reranker,
        treatment_repository=treatment_repository,
        patient_repository=patient_repository,
        summarizer=summarizer,
        rag_pipeline=rag_pipeline,
        prompt_builder=prompt_builder,
        tool_registry=tool_registry,
        treatment_service=treatment_service,
        patient_service=patient_service,
        reminder_service=reminder_service,
        orchestrator=orchestrator,
        conversation_service=conversation_service,
        inbox_service=inbox_service,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    app.state.container = _build_container(settings)
    logger.info("Container initialized")
    yield


app = FastAPI(lifespan=lifespan)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(webhook_route.router)
app.include_router(reminders_route.router)
app.include_router(sandbox_route.router)
