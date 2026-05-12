import { api } from "../../lib/api";

type TranscriptionStatus = {
  provider: string;
  mode: string;
  ready: boolean;
  can_transcribe: boolean;
  label: string;
  message: string;
  model?: string | null;
  device?: string | null;
  compute_type?: string | null;
};

async function getTranscriptionStatus() {
  try {
    const response = await api("/transcription/status");
    return (await response.json()) as TranscriptionStatus;
  } catch {
    return null;
  }
}

export default async function Settings() {
  const transcriptionStatus = await getTranscriptionStatus();

  return (
    <main className="page">
      <section className="page-header">
        <div>
          <p className="eyebrow">Configuration</p>
          <h2>Settings</h2>
          <p className="lead">
            Backend environment variables control model access and local
            storage for this MVP.
          </p>
        </div>
      </section>

      <section className="grid two settings-grid">
        <article className="panel setting-card">
          <span className="setting-icon" aria-hidden="true">
            AI
          </span>
          <h3>LLM provider</h3>
          <p className="summary-copy">
            Set <code>OPENROUTER_API_KEY</code> in the backend environment to
            enable processing.
          </p>
        </article>
        <article className="panel setting-card">
          <span className="setting-icon" aria-hidden="true">
            M
          </span>
          <h3>Default model</h3>
          <p className="summary-copy">
            Set <code>OPENROUTER_DEFAULT_MODEL</code> to choose the model used
            for meeting summaries.
          </p>
        </article>
        <article className="panel setting-card">
          <span className="setting-icon" aria-hidden="true">
            STT
          </span>
          <div className="section-heading compact">
            <h3>Transcription provider</h3>
            <span
              className={`status ${
                transcriptionStatus?.can_transcribe ? "completed" : "uploaded"
              }`}
            >
              {transcriptionStatus?.label || "Unavailable"}
            </span>
          </div>
          <p className="summary-copy">
            {transcriptionStatus?.message ||
              "The backend transcription provider status could not be loaded."}
          </p>
          {transcriptionStatus ? (
            <p className="summary-copy">
              Provider: <code>{transcriptionStatus.provider}</code>
              {transcriptionStatus.model ? (
                <>
                  {" "}
                  / Model: <code>{transcriptionStatus.model}</code>
                </>
              ) : null}
            </p>
          ) : null}
        </article>
      </section>
    </main>
  );
}
