"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { API_BASE_URL } from "../../../lib/api";

type CreatedMeeting = {
  id: number;
};

type InputMode = "transcript" | "upload";

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
  const [tags, setTags] = useState("");
  const [workspaceId, setWorkspaceId] = useState("1");
  const [inputMode, setInputMode] = useState<InputMode>("transcript");
  const [transcript, setTranscript] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const transcriptStats = useMemo(() => {
    const trimmed = transcript.trim();
    return {
      characters: trimmed.length,
      words: trimmed ? trimmed.split(/\s+/).length : 0,
    };
  }, [transcript]);

  const canSubmit =
    title.trim().length > 0 &&
    (inputMode === "transcript" ? transcript.trim().length > 0 : Boolean(file));
  const transcriptReadiness = Math.min(
    100,
    Math.round((transcriptStats.words / 600) * 100),
  );
  const fileSize = file ? file.size / 1024 / 1024 : 0;
  const parsedTags = useMemo(
    () =>
      Array.from(
        new Set(
          tags
            .split(",")
            .map((tag) => tag.trim().toLowerCase())
            .filter(Boolean),
        ),
      ).slice(0, 12),
    [tags],
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
        source_type: inputMode === "transcript" ? "transcript" : "upload",
        tags: parsedTags,
      });

      if (inputMode === "transcript") {
        await postJson(`/meetings/${meeting.id}/transcript`, {
          transcript_text: transcript.trim(),
        });
      } else if (file) {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch(`${API_BASE_URL}/meetings/${meeting.id}/upload`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          throw new Error(await response.text());
        }
      }

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
          <p className="eyebrow">New meeting</p>
          <h2>Create meeting</h2>
          <p className="lead">
            Add a pasted transcript for immediate AI notes, or upload audio/video
            now and transcribe it in the next product phase.
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

          <div className="segmented-control wide-control" aria-label="Meeting input mode">
            <button
              className={inputMode === "transcript" ? "active" : ""}
              onClick={() => setInputMode("transcript")}
              type="button"
            >
              Transcript
            </button>
            <button
              className={inputMode === "upload" ? "active" : ""}
              onClick={() => setInputMode("upload")}
              type="button"
            >
              Audio/video
            </button>
          </div>

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
            <span className="label">Tags</span>
            <input
              className="input"
              onChange={(event) => setTags(event.target.value)}
              placeholder="customer-call, product, sprint"
              value={tags}
            />
            {parsedTags.length ? (
              <span className="helper">
                {parsedTags.length} tag{parsedTags.length === 1 ? "" : "s"} will be saved.
              </span>
            ) : null}
          </label>

          {inputMode === "transcript" ? (
            <label className="field">
              <span className="label">Transcript</span>
              <textarea
                className="textarea"
                value={transcript}
                onChange={(event) => setTranscript(event.target.value)}
                placeholder="Paste the full transcript here..."
              />
            </label>
          ) : (
            <label className="field upload-field">
              <span className="label">Audio or video file</span>
              <input
                accept="audio/*,video/*"
                className="input"
                onChange={(event) => setFile(event.target.files?.[0] || null)}
                type="file"
              />
              <span className="helper">
                This saves the original recording. Transcription is the next phase.
              </span>
            </label>
          )}

          <div className="actions">
            <button className="button primary" disabled={!canSubmit || isSubmitting}>
              {isSubmitting
                ? inputMode === "upload"
                  ? "Uploading..."
                  : "Creating..."
                : "Create meeting"}
            </button>
            <Link className="button" href="/meetings">
              Cancel
            </Link>
          </div>
        </form>

        <aside className="panel inspector-panel">
          {inputMode === "transcript" ? (
            <>
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
            </>
          ) : (
            <>
              <div className="section-heading compact">
                <div>
                  <p className="eyebrow">Upload check</p>
                  <h3>Recording intake</h3>
                </div>
              </div>

              <div className="stat-pair">
                <div>
                  <span className="metric-label">Selected</span>
                  <strong>{file ? "Yes" : "No"}</strong>
                </div>
                <div>
                  <span className="metric-label">Size</span>
                  <strong>{file ? `${fileSize.toFixed(1)} MB` : "0 MB"}</strong>
                </div>
              </div>

              <ul className="check-list" aria-label="Upload preparation checklist">
                <li className={title.trim() ? "complete" : ""}>Meeting title added</li>
                <li className={file ? "complete" : ""}>Recording selected</li>
                <li>Transcription provider pending</li>
              </ul>

              <p className="footer-note">
                Uploaded recordings are stored on the backend and marked as uploaded.
                The transcription provider will be connected next.
              </p>
            </>
          )}
        </aside>
      </section>
    </main>
  );
}
