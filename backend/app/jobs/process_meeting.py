from sqlalchemy.orm import Session
from app.models.models import Meeting, MeetingStatus, MeetingAIOutput, ActionItem
from app.services.summarization.meeting_summarizer import MeetingSummarizer
from app.services.summarization.quality import evaluate_summary_quality


def processing_error_message(error: Exception) -> str:
    message = str(error).strip() or error.__class__.__name__
    if len(message) > 1200:
        return f"{message[:1200]}..."
    return message


async def process_meeting(
    meeting: Meeting,
    db: Session,
    summarizer: MeetingSummarizer,
    provider_name: str,
    model: str,
):
    meeting.status = MeetingStatus.summarizing
    meeting.processing_error = None
    db.commit()
    try:
        summary = await summarizer.summarize_transcript(meeting.transcript_text or "")
        quality = evaluate_summary_quality(meeting.transcript_text or "", summary)
        if summarizer.last_processing_info:
            quality["processing"] = summarizer.last_processing_info
        output = db.query(MeetingAIOutput).filter_by(meeting_id=meeting.id).first()
        if output:
            output.provider = provider_name
            output.model = model
            output.summary_json = summary.model_dump()
            output.quality_json = quality
        else:
            output = MeetingAIOutput(
                meeting_id=meeting.id,
                provider=provider_name,
                model=model,
                summary_json=summary.model_dump(),
                quality_json=quality,
            )
            db.add(output)

        db.query(ActionItem).filter_by(meeting_id=meeting.id).delete()
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
        meeting.processing_error = None
        db.commit()
    except Exception as e:
        meeting.status = MeetingStatus.failed
        meeting.processing_error = processing_error_message(e)
        db.commit()
        raise
