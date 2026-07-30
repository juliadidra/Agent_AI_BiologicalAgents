from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from google.cloud.firestore_v1.client import Client

from src.core.settings import Settings

if TYPE_CHECKING:
    from src.ports.embedder import Embedder
    from src.ports.llm import GuardrailProvider, LLMProvider
    from src.ports.messaging import MessagingGateway
    from src.ports.patient_repository import PatientRepository
    from src.ports.reranker import Reranker
    from src.ports.summarizer import Summarizer
    from src.ports.treatment_repository import TreatmentRepository
    from src.ports.vector_retriever import VectorRetriever
    from src.services.conversation_service import ConversationService
    from src.services.inbox_service import InboxService
    from src.services.patient_service import PatientService
    from src.services.prompt_builder import PromptBuilder
    from src.services.rag_pipeline import RagPipeline
    from src.services.reminder_service import ReminderService
    from src.services.tool_registry import ToolRegistry
    from src.services.treatment_service import TreatmentService


@dataclass
class Container:
    settings: Settings
    firestore: Client

    messaging: Optional["MessagingGateway"] = None
    llm: Optional["LLMProvider"] = None
    guardrail: Optional["GuardrailProvider"] = None
    embedder: Optional["Embedder"] = None
    vector_retriever: Optional["VectorRetriever"] = None
    reranker: Optional["Reranker"] = None
    treatment_repository: Optional["TreatmentRepository"] = None
    patient_repository: Optional["PatientRepository"] = None
    summarizer: Optional["Summarizer"] = None

    rag_pipeline: Optional["RagPipeline"] = None
    prompt_builder: Optional["PromptBuilder"] = None
    tool_registry: Optional["ToolRegistry"] = None
    treatment_service: Optional["TreatmentService"] = None
    patient_service: Optional["PatientService"] = None
    reminder_service: Optional["ReminderService"] = None
    conversation_service: Optional["ConversationService"] = None
    inbox_service: Optional["InboxService"] = None
