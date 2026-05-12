from app.schemas.summary import MeetingSummarySchema


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
