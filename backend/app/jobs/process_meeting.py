from sqlalchemy.orm import Session
from app.models.models import Meeting, MeetingStatus, MeetingAIOutput, ActionItem
from app.services.summarization.meeting_summarizer import MeetingSummarizer


async def process_meeting(
    meeting: Meeting,
    db: Session,
    summarizer: MeetingSummarizer,
    provider_name: str,
    model: str,
):
    meeting.status = MeetingStatus.summarizing
    db.commit()
    try:
        summary = await summarizer.summarize_transcript(meeting.transcript_text or "")
        output = MeetingAIOutput(
            meeting_id=meeting.id,
            provider=provider_name,
            model=model,
            summary_json=summary.model_dump(),
        )
        db.add(output)
        for ai in summary.action_items:
            db.add(
                ActionItem(
                    meeting_id=meeting.id,
                    task=ai.task,
                    owner=ai.owner,
                    due_date=ai.due_date,
                    priority=ai.priority,
                    evidence=ai.evidence,
                )
            )
        meeting.status = MeetingStatus.completed
        db.commit()
    except Exception:
        meeting.status = MeetingStatus.failed
        db.commit()
        raise
