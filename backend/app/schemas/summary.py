from pydantic import BaseModel


class Decision(BaseModel):
    decision: str
    context: str
    owner: str | None = None


class ActionItemSchema(BaseModel):
    task: str
    owner: str | None = None
    due_date: str | None = None
    priority: str
    evidence: str


class Deliverable(BaseModel):
    deliverable: str
    owner: str | None = None
    due_date: str | None = None


class MeetingSummarySchema(BaseModel):
    title: str
    executive_summary: str
    key_points: list[str]
    decisions: list[Decision]
    action_items: list[ActionItemSchema]
    deliverables: list[Deliverable]
    risks_blockers: list[str]
    open_questions: list[str]
    follow_up_email: str
