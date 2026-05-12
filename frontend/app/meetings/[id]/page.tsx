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
  transcript_source?: string | null;
  transcript_provider?: string | null;
  transcript_model?: string | null;
  transcript_language?: string | null;
  transcript_confidence?: string | null;
  transcript_created_at?: string | null;
  processing_error?: string | null;
  tags?: string[];
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

type QualityIssue = {
  severity: "warning" | "critical" | string;
  message: string;
};

type ProcessingQuality = {
  strategy?: string;
  chunk_count?: number;
  chunk_chars?: number;
  overlap_chars?: number;
  transcript_chars?: number;
};

type QualityReport = {
  score?: number;
  status?: "good" | "needs_review" | "weak" | string;
  issues?: QualityIssue[];
  processing?: ProcessingQuality;
};

type AIOutput = {
  provider: string;
  model: string;
  summary_json: Summary;
  quality_json?: QualityReport | null;
};

type RelatedMeeting = {
  meeting_id: number;
  meeting_title: string;
  status: string;
  source_type: string;
  tags: string[];
  score: number;
  reasons: string[];
  excerpt: string;
};

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
  package_installed?: boolean | null;
};

type EditableSummaryField =
  | "executive_summary"
  | "key_points"
  | "risks_blockers"
  | "open_questions"
  | "follow_up_email";

type RegeneratableSummaryField =
  | "executive_summary"
  | "key_points"
  | "decisions"
  | "action_items"
  | "deliverables"
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
    throw new Error(await getApiErrorMessage(response));
  }

  return response.json() as Promise<T>;
}

async function getApiErrorMessage(response: Response) {
  const text = await response.text();
  if (!text) {
    return response.statusText || "Request failed.";
  }

  try {
    const body = JSON.parse(text) as { detail?: unknown };
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((item) => {
          if (
            item &&
            typeof item === "object" &&
            "msg" in item &&
            typeof item.msg === "string"
          ) {
            return item.msg;
          }
          return JSON.stringify(item);
        })
        .join(" ");
    }
  } catch {
    return text;
  }

  return text;
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

function draftToTags(value: string) {
  return Array.from(
    new Set(
      value
        .split(",")
        .map((tag) => tag.trim().toLowerCase())
        .filter(Boolean),
    ),
  ).slice(0, 12);
}

export default function MeetingDetail({ params }: { params: { id: string } }) {
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [output, setOutput] = useState<AIOutput | null>(null);
  const [relatedMeetings, setRelatedMeetings] = useState<RelatedMeeting[]>([]);
  const [transcriptionStatus, setTranscriptionStatus] =
    useState<TranscriptionStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [editingField, setEditingField] = useState<EditableSummaryField | null>(null);
  const [summaryDraft, setSummaryDraft] = useState("");
  const [isSavingSummary, setIsSavingSummary] = useState(false);
  const [regeneratingField, setRegeneratingField] =
    useState<RegeneratableSummaryField | null>(null);
  const [isEditingTags, setIsEditingTags] = useState(false);
  const [tagDraft, setTagDraft] = useState("");
  const [isSavingTags, setIsSavingTags] = useState(false);
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

    try {
      setRelatedMeetings(
        await getJson<RelatedMeeting[]>(`/meetings/${params.id}/related`),
      );
    } catch {
      setRelatedMeetings([]);
    }

    try {
      setTranscriptionStatus(
        await getJson<TranscriptionStatus>("/transcription/status"),
      );
    } catch {
      setTranscriptionStatus(null);
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
        throw new Error(await getApiErrorMessage(response));
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
        throw new Error(await getApiErrorMessage(response));
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

  function startTagEdit() {
    setError("");
    setIsEditingTags(true);
    setTagDraft((meeting?.tags || []).join(", "));
  }

  function cancelTagEdit() {
    setIsEditingTags(false);
    setTagDraft("");
  }

  async function saveTags() {
    if (!meeting || isSavingTags) {
      return;
    }

    setIsSavingTags(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/meetings/${params.id}/tags`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tags: draftToTags(tagDraft) }),
      });

      if (!response.ok) {
        throw new Error(await getApiErrorMessage(response));
      }

      setMeeting((await response.json()) as Meeting);
      cancelTagEdit();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save tags.");
    } finally {
      setIsSavingTags(false);
    }
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
        throw new Error(await getApiErrorMessage(response));
      }

      setOutput((await response.json()) as AIOutput);
      cancelSummaryEdit();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save summary edits.");
    } finally {
      setIsSavingSummary(false);
    }
  }

  async function regenerateSummarySection(field: RegeneratableSummaryField) {
    if (!output || regeneratingField) {
      return;
    }

    setRegeneratingField(field);
    setError("");
    setMeeting((current) =>
      current ? { ...current, status: "summarizing", processing_error: null } : current,
    );

    try {
      const response = await fetch(
        `${API_BASE_URL}/meetings/${params.id}/ai-output/summary/regenerate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ section: field }),
        },
      );

      if (!response.ok) {
        throw new Error(await getApiErrorMessage(response));
      }

      setOutput((await response.json()) as AIOutput);
      cancelSummaryEdit();
      await refresh();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : `Unable to regenerate ${field}.`;
      setError(message);
      setMeeting((current) =>
        current
          ? { ...current, status: "failed", processing_error: message }
          : current,
      );
    } finally {
      setRegeneratingField(null);
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
  const quality = output?.quality_json;
  const canExport = Boolean(output);
  const canProcess = Boolean(meeting.transcript_text);
  const canRegenerate = Boolean(output && meeting.transcript_text);
  const hasUploadedMedia = Boolean(meeting.audio_file_path || meeting.video_file_path);
  const canRealTranscribe = Boolean(transcriptionStatus?.can_transcribe);
  const transcriptionActionLabel = canRealTranscribe
    ? "Transcribe recording"
    : "Create placeholder transcript";
  const summaryStats = [
    { label: "Key points", value: summary?.key_points?.length ?? 0 },
    { label: "Actions", value: summary?.action_items?.length ?? 0 },
    { label: "Decisions", value: summary?.decisions?.length ?? 0 },
  ];
  const processing = quality?.processing;
  const processingStrategy =
    processing?.strategy === "refine" ? "Refine" : "Single pass";

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
            {meeting.tags?.map((tag) => (
              <Link
                className="pill tag-pill"
                href={`/meetings?tag=${encodeURIComponent(tag)}`}
                key={tag}
              >
                {tag}
              </Link>
            ))}
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
      {!error && meeting.status === "failed" && meeting.processing_error ? (
        <div className="alert">
          Processing failed: {meeting.processing_error}
        </div>
      ) : null}

      {hasUploadedMedia && !meeting.transcript_text ? (
        <section className="panel upload-state-panel">
          <div>
            <p className="eyebrow">Recording uploaded</p>
            <h3>{meeting.audio_file_path ? "Audio file attached" : "Video file attached"}</h3>
            <p className="helper">
              {transcriptionStatus?.message ||
                "The recording is saved. Checking the backend transcription provider."}
            </p>
          </div>
          <div className="actions">
            <button
              className="button primary"
              disabled={isTranscribing}
              onClick={() => void transcribeMeeting()}
              type="button"
            >
              {isTranscribing ? "Transcribing..." : transcriptionActionLabel}
            </button>
            <span className={`status ${canRealTranscribe ? "completed" : "uploaded"}`}>
              {transcriptionStatus?.label || "Awaiting transcription"}
            </span>
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
                <div className="actions inline-actions section-tools">
                  <button
                    className="button subtle compact-button"
                    disabled={regeneratingField === "executive_summary"}
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
                  <button
                    className="button subtle compact-button"
                    disabled={!canRegenerate || Boolean(regeneratingField)}
                    onClick={() => void regenerateSummarySection("executive_summary")}
                    type="button"
                  >
                    {regeneratingField === "executive_summary"
                      ? "Regenerating..."
                      : "Regenerate"}
                  </button>
                </div>
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

          {summary ? (
            <article className="panel">
              <div className="section-heading compact">
                <h3>Key points</h3>
                <div className="actions inline-actions section-tools">
                  <button
                    className="button subtle compact-button"
                    disabled={regeneratingField === "key_points"}
                    onClick={() => startSummaryEdit("key_points", summary.key_points || [])}
                    type="button"
                  >
                    Edit
                  </button>
                  <button
                    className="button subtle compact-button"
                    disabled={!canRegenerate || Boolean(regeneratingField)}
                    onClick={() => void regenerateSummarySection("key_points")}
                    type="button"
                  >
                    {regeneratingField === "key_points"
                      ? "Regenerating..."
                      : "Regenerate"}
                  </button>
                </div>
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
              ) : summary.key_points?.length ? (
                <ul className="note-list">
                  {summary.key_points.map((point, index) => (
                    <li key={`${point}-${index}`}>{point}</li>
                  ))}
                </ul>
              ) : (
                <p className="helper">No key points captured yet.</p>
              )}
            </article>
          ) : null}

          {summary ? (
            <article className="panel">
              <div className="section-heading compact">
                <h3>Decisions</h3>
                <button
                  className="button subtle compact-button"
                  disabled={!canRegenerate || Boolean(regeneratingField)}
                  onClick={() => void regenerateSummarySection("decisions")}
                  type="button"
                >
                  {regeneratingField === "decisions"
                    ? "Regenerating..."
                    : "Regenerate"}
                </button>
              </div>
              {summary.decisions?.length ? (
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
              ) : (
                <p className="helper">No decisions captured yet.</p>
              )}
            </article>
          ) : null}

          {summary ? (
            <article className="panel">
              <div className="section-heading compact">
                <h3>Follow-up email</h3>
                <div className="actions inline-actions section-tools">
                  <button
                    className="button subtle compact-button"
                    disabled={regeneratingField === "follow_up_email"}
                    onClick={() =>
                      startSummaryEdit("follow_up_email", summary.follow_up_email || "")
                    }
                    type="button"
                  >
                    Edit
                  </button>
                  <button
                    className="button subtle compact-button"
                    disabled={!canRegenerate || Boolean(regeneratingField)}
                    onClick={() => void regenerateSummarySection("follow_up_email")}
                    type="button"
                  >
                    {regeneratingField === "follow_up_email"
                      ? "Regenerating..."
                      : "Regenerate"}
                  </button>
                </div>
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
              ) : summary.follow_up_email ? (
                <div className="transcript">{summary.follow_up_email}</div>
              ) : (
                <p className="helper">No follow-up email generated yet.</p>
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
            {meeting.transcript_text ? (
              <div className="meta-row transcript-meta">
                <span className="pill">
                  Source: {meeting.transcript_source || "unknown"}
                </span>
                <span className="pill">
                  Provider: {meeting.transcript_provider || "unknown"}
                </span>
                {meeting.transcript_model ? (
                  <span className="pill">Model: {meeting.transcript_model}</span>
                ) : null}
                {meeting.transcript_language ? (
                  <span className="pill">Language: {meeting.transcript_language}</span>
                ) : null}
                {meeting.transcript_confidence ? (
                  <span className="pill">
                    Confidence: {meeting.transcript_confidence}
                  </span>
                ) : null}
              </div>
            ) : null}
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
            <div className="section-heading compact">
              <div>
                <p className="eyebrow">Metadata</p>
                <h3>Tags</h3>
              </div>
              {!isEditingTags ? (
                <button
                  className="button subtle compact-button"
                  onClick={startTagEdit}
                  type="button"
                >
                  Edit
                </button>
              ) : null}
            </div>
            {isEditingTags ? (
              <div className="summary-edit-form">
                <input
                  className="input"
                  onChange={(event) => setTagDraft(event.target.value)}
                  placeholder="customer-call, product, sprint"
                  value={tagDraft}
                />
                <div className="actions inline-actions">
                  <button
                    className="button primary"
                    disabled={isSavingTags}
                    onClick={() => void saveTags()}
                    type="button"
                  >
                    {isSavingTags ? "Saving..." : "Save"}
                  </button>
                  <button
                    className="button"
                    disabled={isSavingTags}
                    onClick={cancelTagEdit}
                    type="button"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : meeting.tags?.length ? (
              <div className="meta-row">
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
            ) : (
              <p className="helper">No tags saved for this meeting.</p>
            )}
          </section>

          <section className="panel">
            <div className="section-heading compact">
              <div>
                <p className="eyebrow">Memory</p>
                <h3>Related meetings</h3>
              </div>
            </div>
            {relatedMeetings.length ? (
              <div className="related-list">
                {relatedMeetings.map((related) => (
                  <Link
                    className="related-item"
                    href={`/meetings/${related.meeting_id}`}
                    key={related.meeting_id}
                  >
                    <div className="related-heading">
                      <strong>{related.meeting_title}</strong>
                      <span className={`status ${related.status}`}>
                        {statusCopy[related.status] || related.status}
                      </span>
                    </div>
                    <p className="helper">{related.excerpt}</p>
                    <div className="meta-row">
                      {related.reasons.map((reason) => (
                        <span className="pill" key={reason}>
                          {reason}
                        </span>
                      ))}
                      {related.tags.slice(0, 2).map((tag) => (
                        <span className="pill tag-pill" key={tag}>
                          {tag}
                        </span>
                      ))}
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="helper">
                Related meetings will appear as tags, summaries, transcripts, and
                action items accumulate.
              </p>
            )}
          </section>

          {quality ? (
            <section className={`panel quality-panel ${quality.status || "good"}`}>
              <div className="section-heading compact">
                <div>
                  <p className="eyebrow">Quality</p>
                  <h3>Summary checks</h3>
                </div>
                <span className={`status ${quality.status || "good"}`}>
                  {quality.status === "needs_review"
                    ? "Needs review"
                    : quality.status || "good"}
                </span>
              </div>
              <div className="quality-score">
                <strong>{quality.score ?? 100}</strong>
                <span className="helper">Quality score</span>
              </div>
              {processing ? (
                <div className="processing-meta">
                  <span>{processingStrategy}</span>
                  <span>{processing.chunk_count || 1} chunk(s)</span>
                  {processing.overlap_chars ? (
                    <span>
                      {processing.overlap_chars.toLocaleString()} overlap chars
                    </span>
                  ) : null}
                </div>
              ) : null}
              {quality.issues?.length ? (
                <ul className="quality-list">
                  {quality.issues.map((issue, index) => (
                    <li
                      className={`quality-issue ${issue.severity}`}
                      key={`${issue.message}-${index}`}
                    >
                      {issue.message}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="helper">
                  No quality warnings found for this summary.
                </p>
              )}
            </section>
          ) : null}

          <section className="panel">
            <div className="section-heading compact">
              <h3>Action items</h3>
              {summary ? (
                <button
                  className="button subtle compact-button"
                  disabled={!canRegenerate || Boolean(regeneratingField)}
                  onClick={() => void regenerateSummarySection("action_items")}
                  type="button"
                >
                  {regeneratingField === "action_items"
                    ? "Regenerating..."
                    : "Regenerate"}
                </button>
              ) : null}
            </div>
            {summary?.action_items?.length ? (
              <div className="section-stack action-scroll-list">
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

          {summary ? (
            <section className="panel">
              <div className="section-heading compact">
                <h3>Deliverables</h3>
                <button
                  className="button subtle compact-button"
                  disabled={!canRegenerate || Boolean(regeneratingField)}
                  onClick={() => void regenerateSummarySection("deliverables")}
                  type="button"
                >
                  {regeneratingField === "deliverables"
                    ? "Regenerating..."
                    : "Regenerate"}
                </button>
              </div>
              {summary.deliverables?.length ? (
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
              ) : (
                <p className="helper">No deliverables captured yet.</p>
              )}
            </section>
          ) : null}

          {summary ? (
            <section className="panel">
              <div className="section-heading compact">
                <h3>Risks and blockers</h3>
                <div className="actions inline-actions section-tools">
                  <button
                    className="button subtle compact-button"
                    disabled={regeneratingField === "risks_blockers"}
                    onClick={() =>
                      startSummaryEdit("risks_blockers", summary.risks_blockers || [])
                    }
                    type="button"
                  >
                    Edit
                  </button>
                  <button
                    className="button subtle compact-button"
                    disabled={!canRegenerate || Boolean(regeneratingField)}
                    onClick={() => void regenerateSummarySection("risks_blockers")}
                    type="button"
                  >
                    {regeneratingField === "risks_blockers"
                      ? "Regenerating..."
                      : "Regenerate"}
                  </button>
                </div>
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
              ) : summary.risks_blockers?.length ? (
                <ul className="note-list">
                  {summary.risks_blockers.map((risk, index) => (
                    <li key={`${risk}-${index}`}>{risk}</li>
                  ))}
                </ul>
              ) : (
                <p className="helper">No risks or blockers captured yet.</p>
              )}
            </section>
          ) : null}

          {summary ? (
            <section className="panel">
              <div className="section-heading compact">
                <h3>Open questions</h3>
                <div className="actions inline-actions section-tools">
                  <button
                    className="button subtle compact-button"
                    disabled={regeneratingField === "open_questions"}
                    onClick={() =>
                      startSummaryEdit("open_questions", summary.open_questions || [])
                    }
                    type="button"
                  >
                    Edit
                  </button>
                  <button
                    className="button subtle compact-button"
                    disabled={!canRegenerate || Boolean(regeneratingField)}
                    onClick={() => void regenerateSummarySection("open_questions")}
                    type="button"
                  >
                    {regeneratingField === "open_questions"
                      ? "Regenerating..."
                      : "Regenerate"}
                  </button>
                </div>
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
              ) : summary.open_questions?.length ? (
                <ul className="note-list">
                  {summary.open_questions.map((question, index) => (
                    <li key={`${question}-${index}`}>{question}</li>
                  ))}
                </ul>
              ) : (
                <p className="helper">No open questions captured yet.</p>
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
