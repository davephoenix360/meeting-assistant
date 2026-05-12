"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { API_BASE_URL } from "../../../lib/api";

type Meeting = {
  id: number;
  title: string;
  status: string;
  source_type: string;
  transcript_text?: string | null;
};

type Decision = {
  decision: string;
  context?: string;
  owner?: string | null;
};

type ActionItem = {
  task: string;
  owner?: string | null;
  due_date?: string | null;
  priority?: string | null;
  evidence?: string | null;
};

type Deliverable = {
  deliverable: string;
  owner?: string | null;
  due_date?: string | null;
};

type Summary = {
  title?: string;
  executive_summary?: string;
  key_points?: string[];
  decisions?: Decision[];
  action_items?: ActionItem[];
  deliverables?: Deliverable[];
  risks_blockers?: string[];
  open_questions?: string[];
  follow_up_email?: string;
};

type AIOutput = {
  provider: string;
  model: string;
  summary_json: Summary;
};

const statusCopy: Record<string, string> = {
  created: "Draft",
  uploaded: "Uploaded",
  transcribing: "Transcribing",
  transcribed: "Ready to process",
  summarizing: "Processing",
  completed: "Completed",
  failed: "Failed",
};

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<T>;
}

export default function MeetingDetail({ params }: { params: { id: string } }) {
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [output, setOutput] = useState<AIOutput | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setError("");
    const nextMeeting = await getJson<Meeting>(`/meetings/${params.id}`);
    setMeeting(nextMeeting);

    try {
      setOutput(await getJson<AIOutput>(`/meetings/${params.id}/ai-output`));
    } catch {
      setOutput(null);
    }
  }, [params.id]);

  async function processMeeting() {
    if (isProcessing) {
      return;
    }

    setIsProcessing(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/meetings/${params.id}/process`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to process meeting.");
    } finally {
      setIsProcessing(false);
    }
  }

  useEffect(() => {
    refresh()
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Unable to load meeting.");
      })
      .finally(() => setIsLoading(false));
  }, [refresh]);

  if (isLoading) {
    return (
      <main className="page">
        <div className="panel">Loading meeting...</div>
      </main>
    );
  }

  if (!meeting) {
    return (
      <main className="page">
        <div className="alert">Meeting could not be loaded.</div>
      </main>
    );
  }

  const summary = output?.summary_json;
  const canExport = Boolean(output);
  const canProcess = Boolean(meeting.transcript_text);
  const summaryStats = [
    { label: "Key points", value: summary?.key_points?.length ?? 0 },
    { label: "Actions", value: summary?.action_items?.length ?? 0 },
    { label: "Decisions", value: summary?.decisions?.length ?? 0 },
  ];

  return (
    <main className="page">
      <section className="page-header detail-header">
        <div>
          <p className="eyebrow">Meeting detail</p>
          <h2>{summary?.title || meeting.title}</h2>
          <div className="meta-row">
            <span className={`status ${meeting.status}`}>
              {statusCopy[meeting.status] ?? meeting.status}
            </span>
            <span className="pill">{meeting.source_type.replace("_", " ")}</span>
            {output ? <span className="pill">{output.model}</span> : null}
          </div>
        </div>
        <div className="actions">
          <button
            className="button primary"
            disabled={!canProcess || isProcessing}
            onClick={() => void processMeeting()}
          >
            {isProcessing ? "Processing..." : output ? "Process again" : "Process notes"}
          </button>
          <a
            className={`button ${canExport ? "" : "subtle disabled"}`}
            aria-disabled={!canExport}
            href={
              canExport
                ? `${API_BASE_URL}/meetings/${params.id}/export/markdown`
                : undefined
            }
          >
            Export Markdown
          </a>
        </div>
      </section>

      {error ? <div className="alert">{error}</div> : null}

      <section className="grid three stat-grid detail-stats" aria-label="Summary totals">
        {summaryStats.map((stat) => (
          <div className="card metric compact-metric" key={stat.label}>
            <span className="metric-label">{stat.label}</span>
            <strong className="metric-value">{stat.value}</strong>
          </div>
        ))}
      </section>

      <section className={`detail-layout ${error ? "with-alert" : ""}`}>
        <div className="section-stack">
          <article className="panel summary-panel">
            <div className="section-heading compact">
              <div>
                <p className="eyebrow">Brief</p>
                <h3>Executive summary</h3>
              </div>
            </div>
            {summary?.executive_summary ? (
              <p className="summary-copy">{summary.executive_summary}</p>
            ) : (
              <p className="helper">
                Process this meeting to generate the executive summary.
              </p>
            )}
          </article>

          {summary?.key_points?.length ? (
            <article className="panel">
              <h3>Key points</h3>
              <ul className="note-list">
                {summary.key_points.map((point, index) => (
                  <li key={`${point}-${index}`}>{point}</li>
                ))}
              </ul>
            </article>
          ) : null}

          {summary?.decisions?.length ? (
            <article className="panel">
              <h3>Decisions</h3>
              <div className="section-stack">
                {summary.decisions.map((decision, index) => (
                  <div className="decision" key={`${decision.decision}-${index}`}>
                    <strong>{decision.decision}</strong>
                    {decision.context ? (
                      <span className="helper">{decision.context}</span>
                    ) : null}
                    {decision.owner ? (
                      <span className="pill">Owner: {decision.owner}</span>
                    ) : null}
                  </div>
                ))}
              </div>
            </article>
          ) : null}

          {summary?.follow_up_email ? (
            <article className="panel">
              <h3>Follow-up email</h3>
              <div className="transcript">{summary.follow_up_email}</div>
            </article>
          ) : null}

          <article className="panel">
            <div className="section-heading compact">
              <div>
                <p className="eyebrow">Source</p>
                <h3>Transcript</h3>
              </div>
            </div>
            <div className="transcript">
              {meeting.transcript_text || "No transcript has been added."}
            </div>
          </article>
        </div>

        <aside className="section-stack">
          <section className="panel">
            <h3>Action items</h3>
            {summary?.action_items?.length ? (
              <div className="section-stack">
                {summary.action_items.map((item, index) => (
                  <div className="action-item" key={`${item.task}-${index}`}>
                    <strong>{item.task}</strong>
                    <div className="meta-row">
                      <span className="pill">{item.priority || "medium"}</span>
                      <span className="pill">{item.owner || "Unassigned"}</span>
                      {item.due_date ? <span className="pill">{item.due_date}</span> : null}
                    </div>
                    {item.evidence ? (
                      <span className="helper">{item.evidence}</span>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <p className="helper">Action items will appear after processing.</p>
            )}
          </section>

          {summary?.deliverables?.length ? (
            <section className="panel">
              <h3>Deliverables</h3>
              <div className="section-stack">
                {summary.deliverables.map((item, index) => (
                  <div className="action-item" key={`${item.deliverable}-${index}`}>
                    <strong>{item.deliverable}</strong>
                    <div className="meta-row">
                      <span className="pill">{item.owner || "Unassigned"}</span>
                      {item.due_date ? <span className="pill">{item.due_date}</span> : null}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          {summary?.risks_blockers?.length ? (
            <section className="panel">
              <h3>Risks and blockers</h3>
              <ul className="note-list">
                {summary.risks_blockers.map((risk, index) => (
                  <li key={`${risk}-${index}`}>{risk}</li>
                ))}
              </ul>
            </section>
          ) : null}

          {summary?.open_questions?.length ? (
            <section className="panel">
              <h3>Open questions</h3>
              <ul className="note-list">
                {summary.open_questions.map((question, index) => (
                  <li key={`${question}-${index}`}>{question}</li>
                ))}
              </ul>
            </section>
          ) : null}

          <Link className="button" href="/meetings">
            Back to meetings
          </Link>
        </aside>
      </section>
    </main>
  );
}
