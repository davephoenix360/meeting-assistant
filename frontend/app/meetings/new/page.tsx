"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { API_BASE_URL } from "../../../lib/api";

type CreatedMeeting = {
  id: number;
};

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<T>;
}

export default function NewMeeting() {
  const [title, setTitle] = useState("");
  const [workspaceId, setWorkspaceId] = useState("1");
  const [transcript, setTranscript] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const transcriptStats = useMemo(() => {
    const trimmed = transcript.trim();
    return {
      characters: trimmed.length,
      words: trimmed ? trimmed.split(/\s+/).length : 0,
    };
  }, [transcript]);

  const canSubmit = title.trim().length > 0 && transcript.trim().length > 0;
  const transcriptReadiness = Math.min(
    100,
    Math.round((transcriptStats.words / 600) * 100),
  );

  async function submit() {
    if (!canSubmit || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setError("");

    try {
      const meeting = await postJson<CreatedMeeting>("/meetings", {
        title: title.trim(),
        workspace_id: Number(workspaceId),
        source_type: "transcript",
      });

      await postJson(`/meetings/${meeting.id}/transcript`, {
        transcript_text: transcript.trim(),
      });

      window.location.href = `/meetings/${meeting.id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create meeting.");
      setIsSubmitting(false);
    }
  }

  return (
    <main className="page">
      <section className="page-header">
        <div>
          <p className="eyebrow">New transcript</p>
          <h2>Create meeting</h2>
          <p className="lead">
            Add the meeting context and paste the transcript. You can process
            the notes from the meeting page after it is saved.
          </p>
        </div>
        <div className="actions">
          <Link className="button subtle" href="/meetings">
            Back to meetings
          </Link>
        </div>
      </section>

      <section className="split compose-layout">
        <form
          className="panel form"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          {error ? <div className="alert">{error}</div> : null}

          <label className="field">
            <span className="label">Meeting title</span>
            <input
              className="input"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Weekly product sync"
            />
          </label>

          <label className="field">
            <span className="label">Workspace ID</span>
            <input
              className="input"
              inputMode="numeric"
              value={workspaceId}
              onChange={(event) => setWorkspaceId(event.target.value)}
            />
          </label>

          <label className="field">
            <span className="label">Transcript</span>
            <textarea
              className="textarea"
              value={transcript}
              onChange={(event) => setTranscript(event.target.value)}
              placeholder="Paste the full transcript here..."
            />
          </label>

          <div className="actions">
            <button className="button primary" disabled={!canSubmit || isSubmitting}>
              {isSubmitting ? "Creating..." : "Create meeting"}
            </button>
            <Link className="button" href="/meetings">
              Cancel
            </Link>
          </div>
        </form>

        <aside className="panel inspector-panel">
          <div className="section-heading compact">
            <div>
              <p className="eyebrow">Quality check</p>
              <h3>Transcript health</h3>
            </div>
          </div>

          <div className="progress-block">
            <div className="progress-label">
              <span>Context depth</span>
              <strong>{transcriptReadiness}%</strong>
            </div>
            <div className="progress-track" aria-hidden="true">
              <span style={{ width: `${transcriptReadiness}%` }} />
            </div>
          </div>

          <div className="stat-pair">
            <div>
              <span className="metric-label">Words</span>
              <strong>{transcriptStats.words.toLocaleString()}</strong>
            </div>
            <div>
              <span className="metric-label">Characters</span>
              <strong>{transcriptStats.characters.toLocaleString()}</strong>
            </div>
          </div>

          <ul className="check-list" aria-label="Transcript preparation checklist">
            <li className={title.trim() ? "complete" : ""}>Meeting title added</li>
            <li className={transcriptStats.words > 0 ? "complete" : ""}>
              Transcript pasted
            </li>
            <li className={transcriptStats.words >= 120 ? "complete" : ""}>
              Enough context for useful notes
            </li>
          </ul>

          <p className="footer-note">
            Longer transcripts produce better context, but the summary depends
            most on clear speaker turns, decisions, and action language.
          </p>
        </aside>
      </section>
    </main>
  );
}
