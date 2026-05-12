import Link from "next/link";
import { api } from "../../lib/api";
import { SavedViewsClient } from "./SavedViewsClient";
import {
  meetingFiltersHref,
  type MeetingFilters,
  type SavedMeetingView,
} from "./filters";

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
    q?: string;
    tag?: string;
    status?: string;
    source_type?: string;
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

const statusOptions = [
  ["", "Any status"],
  ["created", "Draft"],
  ["uploaded", "Uploaded"],
  ["transcribing", "Transcribing"],
  ["transcribed", "Ready"],
  ["summarizing", "Processing"],
  ["completed", "Completed"],
  ["failed", "Failed"],
];

const sourceOptions = [
  ["", "Any source"],
  ["transcript", "Transcript"],
  ["upload", "Upload"],
  ["zoom", "Zoom"],
  ["google_meet", "Google Meet"],
  ["teams", "Teams"],
];

export default async function MeetingsPage({ searchParams }: Props) {
  const filters: MeetingFilters = {
    q: (searchParams?.q || "").trim(),
    tag: (searchParams?.tag || "").trim(),
    status: (searchParams?.status || "").trim(),
    source_type: (searchParams?.source_type || "").trim(),
  };
  const meetingsPath = meetingFiltersHref(filters);
  const activeFilterCount = Object.values(filters).filter(Boolean).length;
  const [meetings, tags, savedViews] = await Promise.all([
    (await api(meetingsPath)).json() as Promise<Meeting[]>,
    (await api("/tags")).json() as Promise<string[]>,
    (await api("/meeting-views?workspace_id=1")).json() as Promise<SavedMeetingView[]>,
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
            Review processed notes, continue drafts, or reuse saved filters.
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
          <span className="pill">{meetings.length} shown</span>
        </div>

        <form className="library-filter-form" action="/meetings">
          <label className="field">
            <span className="label">Search</span>
            <input
              className="input compact-input"
              defaultValue={filters.q}
              name="q"
              placeholder="Title, transcript, or tag"
            />
          </label>
          <label className="field">
            <span className="label">Tag</span>
            <select className="input compact-input" defaultValue={filters.tag} name="tag">
              <option value="">Any tag</option>
              {tags.map((tag) => (
                <option key={tag} value={tag}>
                  {tag}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="label">Status</span>
            <select
              className="input compact-input"
              defaultValue={filters.status}
              name="status"
            >
              {statusOptions.map(([value, label]) => (
                <option key={value || "any"} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="label">Source</span>
            <select
              className="input compact-input"
              defaultValue={filters.source_type}
              name="source_type"
            >
              {sourceOptions.map(([value, label]) => (
                <option key={value || "any"} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <div className="actions library-filter-actions">
            <button className="button primary compact-button" type="submit">
              Apply
            </button>
            <Link className="button compact-button" href="/meetings">
              Clear
            </Link>
          </div>
        </form>

        <SavedViewsClient currentFilters={filters} initialViews={savedViews} />

        {activeFilterCount ? (
          <div className="tag-filter-bar" aria-label="Active meeting filters">
            <span className="pill">{activeFilterCount} active filter{activeFilterCount === 1 ? "" : "s"}</span>
            {filters.q ? <span className="pill">Search: {filters.q}</span> : null}
            {filters.tag ? <span className="pill tag-pill">{filters.tag}</span> : null}
            {filters.status ? (
              <span className={`status ${filters.status}`}>{statusCopy[filters.status] || filters.status}</span>
            ) : null}
            {filters.source_type ? <span className="pill">{formatSource(filters.source_type)}</span> : null}
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
                            href={meetingFiltersHref({ ...filters, tag })}
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
