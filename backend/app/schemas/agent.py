from pydantic import BaseModel, Field


class AgentAction(BaseModel):
    action: str
    content: str


class AgentDecision(BaseModel):
    reasoning: str
    actions: list[AgentAction] = Field(default_factory=list)
    sleep_minutes: int = Field(default=5, ge=1, le=60)