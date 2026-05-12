import Link from "next/link";

export default function Home() {
  return (
    <main className="page home-page">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">AI meeting notes</p>
          <h1>Meeting Assistant</h1>
          <p className="lead">
            Convert dense transcripts into concise summaries, decisions, risks,
            and follow-up tasks without losing the important context.
          </p>
          <div className="actions">
            <Link className="button primary" href="/meetings/new">
              Create meeting
            </Link>
            <Link className="button" href="/meetings">
              View workspace
            </Link>
          </div>
        </div>

        <aside className="hero-preview" aria-label="Summary preview">
          <div className="preview-toolbar">
            <span className="status completed">Completed</span>
            <span className="pill">GPT summary</span>
          </div>
          <h3>Product sync recap</h3>
          <p className="summary-copy">
            Roadmap scope is approved, customer migration risk needs owner
            review, and the launch checklist is due before Friday.
          </p>
          <div className="mini-list">
            <span>3 decisions captured</span>
            <span>5 action items assigned</span>
            <span>Markdown export ready</span>
          </div>
        </aside>
      </section>

      <section className="grid three feature-grid" aria-label="Workflow overview">
        <div className="card metric accent-blue">
          <span className="metric-label">Capture</span>
          <strong className="metric-value">Paste</strong>
          <span className="helper">Start with a meeting title and transcript.</span>
        </div>
        <div className="card metric accent-green">
          <span className="metric-label">Distill</span>
          <strong className="metric-value">Process</strong>
          <span className="helper">Generate summaries, risks, and decisions.</span>
        </div>
        <div className="card metric accent-amber">
          <span className="metric-label">Follow up</span>
          <strong className="metric-value">Share</strong>
          <span className="helper">Export Markdown notes and action items.</span>
        </div>
      </section>
    </main>
  );
}
