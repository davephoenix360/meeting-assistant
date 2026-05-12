from app.schemas.summary import MeetingSummarySchema


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
    def __init__(self, llm_provider, model: str):
        self.llm_provider = llm_provider
        self.model = model

    async def summarize_transcript(self, transcript: str) -> MeetingSummarySchema:
        schema = MeetingSummarySchema.model_json_schema()
        messages = [
            {"role": "system", "content": "You extract structured meeting notes in strict JSON."},
            {"role": "user", "content": transcript[:120000]},
        ]
        data = await self.llm_provider.generate_json(messages=messages, schema=schema, model=self.model)
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
