from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    telegram_id: int
    username: str | None
    first_name: str | None
    model_config = ConfigDict(from_attributes=True)


class CommunityOut(BaseModel):
    id: int
    telegram_chat_id: int
    title: str
    kind: str
    bot_is_admin: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    body: str = Field(min_length=1, max_length=4000)


class TemplateOut(BaseModel):
    id: int
    name: str
    body: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
