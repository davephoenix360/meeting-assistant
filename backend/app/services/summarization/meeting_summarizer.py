from pydantic import BaseModel

from app.schemas.summary import (
    ActionItemSchema,
    Decision,
    Deliverable,
    MeetingSummarySchema,
)


REGENERATABLE_SECTIONS = {
    "executive_summary",
    "key_points",
    "decisions",
    "action_items",
    "deliverables",
    "risks_blockers",
    "open_questions",
    "follow_up_email",
}


class MeetingSummarizer:
    def __init__(
        self,
        llm_provider,
        model: str,
        *,
        refine_threshold_chars: int = 60000,
        refine_chunk_chars: int = 30000,
        refine_overlap_chars: int = 1800,
    ):
        self.llm_provider = llm_provider
        self.model = model
        self.refine_threshold_chars = refine_threshold_chars
        self.refine_chunk_chars = refine_chunk_chars
        self.refine_overlap_chars = refine_overlap_chars
        self.last_processing_info: dict = {}

    async def summarize_transcript(self, transcript: str) -> MeetingSummarySchema:
        if len(transcript) > self.refine_threshold_chars:
            return await self.summarize_long_transcript(transcript)

        schema = MeetingSummarySchema.model_json_schema()
        messages = [
            {
                "role": "system",
                "content": (
                    "You extract structured meeting notes in strict JSON. "
                    "Use only facts supported by the transcript."
                ),
            },
            {"role": "user", "content": transcript[:120000]},
        ]
        data = await self.llm_provider.generate_json(
            messages=messages,
            schema=schema,
            model=self.model,
        )
        self.last_processing_info = {
            "strategy": "single_pass",
            "chunk_count": 1,
            "transcript_chars": len(transcript),
        }
        return MeetingSummarySchema.model_validate(data)

    async def summarize_long_transcript(self, transcript: str) -> MeetingSummarySchema:
        chunks = split_transcript_for_refine(
            transcript,
            chunk_chars=self.refine_chunk_chars,
            overlap_chars=self.refine_overlap_chars,
        )
        if len(chunks) <= 1:
            return await self.summarize_transcript(
                transcript[: self.refine_threshold_chars]
            )

        state_schema = RefineMeetingState.model_json_schema()
        state: RefineMeetingState | None = None
        previous_overlap = ""
        chunk_count = len(chunks)

        for index, chunk in enumerate(chunks, start=1):
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You maintain a running structured memory of a long meeting transcript. "
                        "Return strict JSON only. Preserve important prior facts, entities, "
                        "decisions, action items, deliverables, risks, and open questions. "
                        "Use only facts supported by the existing state and new transcript chunk."
                    ),
                },
                {
                    "role": "user",
                    "content": build_refine_prompt(
                        chunk=chunk,
                        chunk_index=index,
                        chunk_count=chunk_count,
                        existing_state=state,
                        previous_overlap=previous_overlap,
                    ),
                },
            ]
            data = await self.llm_provider.generate_json(
                messages=messages,
                schema=state_schema,
                model=self.model,
            )
            state = RefineMeetingState.model_validate(data)
            previous_overlap = chunk[-self.refine_overlap_chars :]

        assert state is not None
        final_schema = MeetingSummarySchema.model_json_schema()
        final_messages = [
            {
                "role": "system",
                "content": (
                    "You convert long-meeting working memory into polished structured "
                    "meeting notes. Return strict JSON matching the schema. Do not invent "
                    "facts outside the supplied working memory."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Create the final meeting notes from this refined state.\n\n"
                    f"Refined state JSON:\n{state.model_dump_json()}"
                ),
            },
        ]
        data = await self.llm_provider.generate_json(
            messages=final_messages,
            schema=final_schema,
            model=self.model,
        )
        self.last_processing_info = {
            "strategy": "refine",
            "chunk_count": chunk_count,
            "chunk_chars": self.refine_chunk_chars,
            "overlap_chars": self.refine_overlap_chars,
            "transcript_chars": len(transcript),
        }
        return MeetingSummarySchema.model_validate(data)

    async def regenerate_section(
        self,
        transcript: str,
        current_summary: MeetingSummarySchema,
        section: str,
    ) -> object:
        if section not in REGENERATABLE_SECTIONS:
            raise ValueError(f"Unsupported summary section: {section}")

        full_schema = MeetingSummarySchema.model_json_schema()
        section_schema = {
            "type": "object",
            "properties": {section: full_schema["properties"][section]},
            "required": [section],
            "additionalProperties": False,
        }
        if "$defs" in full_schema:
            section_schema["$defs"] = full_schema["$defs"]

        messages = [
            {
                "role": "system",
                "content": (
                    "You improve one section of structured meeting notes. "
                    "Return strict JSON with only the requested property. "
                    "Use only facts supported by the transcript. Preserve the "
                    "same schema and tone as the current notes."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Regenerate this section: {section}\n\n"
                    f"Current full summary JSON:\n{current_summary.model_dump_json()}\n\n"
                    f"Transcript:\n{transcript[:120000]}"
                ),
            },
        ]
        data = await self.llm_provider.generate_json(
            messages=messages, schema=section_schema, model=self.model
        )
        return data[section]


class RefineMeetingState(BaseModel):
    title: str
    running_summary: str
    key_entities: list[str]
    key_points: list[str]
    decisions: list[Decision]
    action_items: list[ActionItemSchema]
    deliverables: list[Deliverable]
    risks_blockers: list[str]
    open_questions: list[str]
    follow_up_email_notes: str


def split_transcript_for_refine(
    transcript: str,
    *,
    chunk_chars: int,
    overlap_chars: int,
) -> list[str]:
    text = transcript.strip()
    if not text:
        return [""]

    chunk_chars = max(8000, chunk_chars)
    overlap_chars = max(0, min(overlap_chars, chunk_chars // 3))

    chunks: list[str] = []
    start = 0
    text_length = len(text)
    while start < text_length:
        target_end = min(text_length, start + chunk_chars)
        end = paragraph_boundary(text, start, target_end)
        if end <= start:
            end = target_end

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break
        start = max(0, end - overlap_chars)

    return chunks


def paragraph_boundary(text: str, start: int, target_end: int) -> int:
    if target_end >= len(text):
        return len(text)

    window_start = start + max(0, int((target_end - start) * 0.72))
    candidates = [
        text.rfind("\n\n", window_start, target_end),
        text.rfind("\n", window_start, target_end),
        text.rfind(". ", window_start, target_end),
    ]
    boundary = max(candidates)
    if boundary <= start:
        return target_end
    return boundary + (2 if text[boundary : boundary + 2] == ". " else 1)


def build_refine_prompt(
    *,
    chunk: str,
    chunk_index: int,
    chunk_count: int,
    existing_state: RefineMeetingState | None,
    previous_overlap: str,
) -> str:
    if existing_state is None:
        existing = "No existing state yet. Initialize it from this first chunk."
    else:
        existing = existing_state.model_dump_json()

    return (
        f"Chunk {chunk_index} of {chunk_count}\n\n"
        f"Existing state:\n{existing}\n\n"
        f"Boundary overlap from prior chunk:\n{previous_overlap}\n\n"
        "New transcript chunk:\n"
        f"{chunk}\n\n"
        "Task: update the state to include this new context without dropping "
        "important prior facts. Keep entity names clear enough that later chunks "
        "can resolve pronouns and references. Deduplicate repeated overlap content."
    )
