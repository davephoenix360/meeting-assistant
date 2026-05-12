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
  audio_file_path?: string | null;
  video_file_path?: string | null;
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

type EditableSummaryField =
  | "executive_summary"
  | "key_points"
  | "risks_blockers"
  | "open_questions"
  | "follow_up_email";

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

function listToDraft(values?: string[]) {
  return values?.join("\n") || "";
}

function draftToList(value: string) {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

export default function MeetingDetail({ params }: { params: { id: string } }) {
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [output, setOutput] = useState<AIOutput | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [editingField, setEditingField] = useState<EditableSummaryField | null>(null);
  const [summaryDraft, setSummaryDraft] = useState("");
  const [isSavingSummary, setIsSavingSummary] = useState(false);
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

  async function transcribeMeeting() {
    if (isTranscribing) {
      return;
    }

    setIsTranscribing(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/meetings/${params.id}/transcribe`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      setMeeting((await response.json()) as Meeting);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to transcribe meeting.");
    } finally {
      setIsTranscribing(false);
    }
  }

  function startSummaryEdit(field: EditableSummaryField, value: string | string[] = "") {
    setError("");
    setEditingField(field);
    setSummaryDraft(Array.isArray(value) ? listToDraft(value) : value);
  }

  function cancelSummaryEdit() {
    setEditingField(null);
    setSummaryDraft("");
  }

  async function saveSummaryEdit(field: EditableSummaryField) {
    if (!output || isSavingSummary) {
      return;
    }

    const listField =
      field === "key_points" ||
      field === "risks_blockers" ||
      field === "open_questions";
    const body = {
      [field]: listField ? draftToList(summaryDraft) : summaryDraft.trim(),
    };

    setIsSavingSummary(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/meetings/${params.id}/ai-output/summary`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );

      if (!response.ok) {
        throw new Error(await response.text());
      }

      setOutput((await response.json()) as AIOutput);
      cancelSummaryEdit();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save summary edits.");
    } finally {
      setIsSavingSummary(false);
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
  const hasUploadedMedia = Boolean(meeting.audio_file_path || meeting.video_file_path);
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

      {hasUploadedMedia && !meeting.transcript_text ? (
        <section className="panel upload-state-panel">
          <div>
            <p className="eyebrow">Recording uploaded</p>
            <h3>{meeting.audio_file_path ? "Audio file attached" : "Video file attached"}</h3>
            <p className="helper">
              The recording is saved. Create a placeholder transcript now, then
              replace it with real provider output when transcription is connected.
            </p>
          </div>
          <div className="actions">
            <button
              className="button primary"
              disabled={isTranscribing}
              onClick={() => void transcribeMeeting()}
              type="button"
            >
              {isTranscribing ? "Transcribing..." : "Create placeholder transcript"}
            </button>
            <span className="status uploaded">Awaiting transcription</span>
          </div>
        </section>
      ) : null}

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
              {summary?.executive_summary ? (
                <button
                  className="button subtle compact-button"
                  onClick={() =>
                    startSummaryEdit(
                      "executive_summary",
                      summary.executive_summary || "",
                    )
                  }
                  type="button"
                >
                  Edit
                </button>
              ) : null}
            </div>
            {editingField === "executive_summary" ? (
              <div className="summary-edit-form">
                <textarea
                  className="textarea summary-editor"
                  onChange={(event) => setSummaryDraft(event.target.value)}
                  value={summaryDraft}
                />
                <div className="actions inline-actions">
                  <button
                    className="button primary"
                    disabled={isSavingSummary}
                    onClick={() => void saveSummaryEdit("executive_summary")}
                    type="button"
                  >
                    {isSavingSummary ? "Saving..." : "Save"}
                  </button>
                  <button
                    className="button"
                    disabled={isSavingSummary}
                    onClick={cancelSummaryEdit}
                    type="button"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : summary?.executive_summary ? (
              <p className="summary-copy">{summary.executive_summary}</p>
            ) : (
              <p className="helper">
                Process this meeting to generate the executive summary.
              </p>
            )}
          </article>

          {summary?.key_points?.length ? (
            <article className="panel">
              <div className="section-heading compact">
                <h3>Key points</h3>
                <button
                  className="button subtle compact-button"
                  onClick={() => startSummaryEdit("key_points", summary.key_points || [])}
                  type="button"
                >
                  Edit
                </button>
              </div>
              {editingField === "key_points" ? (
                <div className="summary-edit-form">
                  <textarea
                    className="textarea summary-editor"
                    onChange={(event) => setSummaryDraft(event.target.value)}
                    value={summaryDraft}
                  />
                  <div className="actions inline-actions">
                    <button
                      className="button primary"
                      disabled={isSavingSummary}
                      onClick={() => void saveSummaryEdit("key_points")}
                      type="button"
                    >
                      {isSavingSummary ? "Saving..." : "Save"}
                    </button>
                    <button
                      className="button"
                      disabled={isSavingSummary}
                      onClick={cancelSummaryEdit}
                      type="button"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <ul className="note-list">
                  {summary.key_points.map((point, index) => (
                    <li key={`${point}-${index}`}>{point}</li>
                  ))}
                </ul>
              )}
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
              <div className="section-heading compact">
                <h3>Follow-up email</h3>
                <button
                  className="button subtle compact-button"
                  onClick={() =>
                    startSummaryEdit("follow_up_email", summary.follow_up_email || "")
                  }
                  type="button"
                >
                  Edit
                </button>
              </div>
              {editingField === "follow_up_email" ? (
                <div className="summary-edit-form">
                  <textarea
                    className="textarea summary-editor tall"
                    onChange={(event) => setSummaryDraft(event.target.value)}
                    value={summaryDraft}
                  />
                  <div className="actions inline-actions">
                    <button
                      className="button primary"
                      disabled={isSavingSummary}
                      onClick={() => void saveSummaryEdit("follow_up_email")}
                      type="button"
                    >
                      {isSavingSummary ? "Saving..." : "Save"}
                    </button>
                    <button
                      className="button"
                      disabled={isSavingSummary}
                      onClick={cancelSummaryEdit}
                      type="button"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="transcript">{summary.follow_up_email}</div>
              )}
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
              {meeting.transcript_text ||
                (hasUploadedMedia
                  ? "No transcript yet. This meeting has an uploaded recording waiting for transcription."
                  : "No transcript has been added.")}
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
              <div className="section-heading compact">
                <h3>Risks and blockers</h3>
                <button
                  className="button subtle compact-button"
                  onClick={() =>
                    startSummaryEdit("risks_blockers", summary.risks_blockers || [])
                  }
                  type="button"
                >
                  Edit
                </button>
              </div>
              {editingField === "risks_blockers" ? (
                <div className="summary-edit-form">
                  <textarea
                    className="textarea summary-editor"
                    onChange={(event) => setSummaryDraft(event.target.value)}
                    value={summaryDraft}
                  />
                  <div className="actions inline-actions">
                    <button
                      className="button primary"
                      disabled={isSavingSummary}
                      onClick={() => void saveSummaryEdit("risks_blockers")}
                      type="button"
                    >
                      {isSavingSummary ? "Saving..." : "Save"}
                    </button>
                    <button
                      className="button"
                      disabled={isSavingSummary}
                      onClick={cancelSummaryEdit}
                      type="button"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <ul className="note-list">
                  {summary.risks_blockers.map((risk, index) => (
                    <li key={`${risk}-${index}`}>{risk}</li>
                  ))}
                </ul>
              )}
            </section>
          ) : null}

          {summary?.open_questions?.length ? (
            <section className="panel">
              <div className="section-heading compact">
                <h3>Open questions</h3>
                <button
                  className="button subtle compact-button"
                  onClick={() =>
                    startSummaryEdit("open_questions", summary.open_questions || [])
                  }
                  type="button"
                >
                  Edit
                </button>
              </div>
              {editingField === "open_questions" ? (
                <div className="summary-edit-form">
                  <textarea
                    className="textarea summary-editor"
                    onChange={(event) => setSummaryDraft(event.target.value)}
                    value={summaryDraft}
                  />
                  <div className="actions inline-actions">
                    <button
                      className="button primary"
                      disabled={isSavingSummary}
                      onClick={() => void saveSummaryEdit("open_questions")}
                      type="button"
                    >
                      {isSavingSummary ? "Saving..." : "Save"}
                    </button>
                    <button
                      className="button"
                      disabled={isSavingSummary}
                      onClick={cancelSummaryEdit}
                      type="button"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <ul className="note-list">
                  {summary.open_questions.map((question, index) => (
                    <li key={`${question}-${index}`}>{question}</li>
                  ))}
                </ul>
              )}
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
