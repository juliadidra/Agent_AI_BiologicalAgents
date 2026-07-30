from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class IncomingMessagePayload(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    chat_id: str = Field(validation_alias=AliasChoices("from", "chatId", "chat_id"))
    body: str = Field(validation_alias=AliasChoices("body", "message", "text"))


class WebhookEnvelope(BaseModel):
    model_config = ConfigDict(extra="allow")

    payload: Optional[dict[str, Any]] = None
