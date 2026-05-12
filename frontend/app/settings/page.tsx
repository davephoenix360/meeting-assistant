export default function Settings() {
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
      </section>
    </main>
  );
}
