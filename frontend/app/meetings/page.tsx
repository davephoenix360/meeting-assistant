import Link from "next/link";
import { api } from "../../lib/api";

type Meeting = {
  id: number;
  title: string;
  source_type: string;
  status: string;
  transcript_text?: string | null;
  tags?: string[];
};

type Props = {
  searchParams?: {
    tag?: string;
  };
};

const statusCopy: Record<string, string> = {
  created: "Draft",
  uploaded: "Uploaded",
  transcribing: "Transcribing",
  transcribed: "Ready",
  summarizing: "Processing",
  completed: "Completed",
  failed: "Failed",
};

function formatSource(source: string) {
  return source.replace("_", " ");
}

export default async function MeetingsPage({ searchParams }: Props) {
  const activeTag = (searchParams?.tag || "").trim();
  const meetingsPath = activeTag
    ? `/meetings?tag=${encodeURIComponent(activeTag)}`
    : "/meetings";
  const [meetings, tags] = await Promise.all([
    (await api(meetingsPath)).json() as Promise<Meeting[]>,
    (await api("/tags")).json() as Promise<string[]>,
  ]);
  const completed = meetings.filter((meeting) => meeting.status === "completed").length;
  const ready = meetings.filter((meeting) => meeting.status === "transcribed").length;

  return (
    <main className="page">
      <section className="page-header">
        <div>
          <p className="eyebrow">Workspace</p>
          <h2>Meetings</h2>
          <p className="lead">
            Review processed notes, continue drafts, or filter meeting memory by tag.
          </p>
        </div>
        <div className="actions">
          <Link className="button primary" href="/meetings/new">
            New meeting
          </Link>
        </div>
      </section>

      <section className="grid three stat-grid" aria-label="Meeting status totals">
        <div className="card metric accent-blue">
          <span className="metric-label">Total</span>
          <strong className="metric-value">{meetings.length}</strong>
          <span className="helper">Meetings in this workspace.</span>
        </div>
        <div className="card metric accent-green">
          <span className="metric-label">Ready</span>
          <strong className="metric-value">{ready}</strong>
          <span className="helper">Transcripts ready to process.</span>
        </div>
        <div className="card metric accent-amber">
          <span className="metric-label">Complete</span>
          <strong className="metric-value">{completed}</strong>
          <span className="helper">Meetings with AI notes.</span>
        </div>
      </section>

      <section className="panel list-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Library</p>
            <h3>Meeting history</h3>
          </div>
          <span className="pill">
            {activeTag ? `${meetings.length} tagged` : `${meetings.length} total`}
          </span>
        </div>

        {tags.length ? (
          <div className="tag-filter-bar" aria-label="Filter meetings by tag">
            <Link className={`pill link-pill ${activeTag ? "" : "active"}`} href="/meetings">
              All
            </Link>
            {tags.map((tag) => (
              <Link
                className={`pill link-pill ${activeTag === tag ? "active" : ""}`}
                href={`/meetings?tag=${encodeURIComponent(tag)}`}
                key={tag}
              >
                {tag}
              </Link>
            ))}
          </div>
        ) : null}

        {meetings.length === 0 ? (
          <div className="empty">
            <div className="empty-inner">
              <h3>No meetings yet</h3>
              <p className="helper">
                Create your first meeting and paste a transcript to generate
                structured notes.
              </p>
              <Link className="button primary" href="/meetings/new">
                Create meeting
              </Link>
            </div>
          </div>
        ) : (
          <ul className="meeting-list">
            {meetings.map((meeting) => (
              <li className="meeting-row" key={meeting.id}>
                <div className="meeting-row-main">
                  <span className="row-marker" aria-hidden="true" />
                  <div>
                    <Link className="meeting-title" href={`/meetings/${meeting.id}`}>
                      {meeting.title}
                    </Link>
                    <span className="helper">
                      {formatSource(meeting.source_type)}
                      {meeting.transcript_text
                        ? ` / ${meeting.transcript_text.length.toLocaleString()} characters`
                        : " / No transcript yet"}
                    </span>
                    {meeting.tags?.length ? (
                      <div className="meta-row meeting-tags">
                        {meeting.tags.map((tag) => (
                          <Link
                            className="pill tag-pill"
                            href={`/meetings?tag=${encodeURIComponent(tag)}`}
                            key={tag}
                          >
                            {tag}
                          </Link>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>
                <span className={`status ${meeting.status}`}>
                  {statusCopy[meeting.status] ?? meeting.status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
