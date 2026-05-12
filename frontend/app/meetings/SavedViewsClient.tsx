"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { API_BASE_URL } from "../../lib/api";
import {
  cleanedFilters,
  meetingFiltersHref,
  type MeetingFilters,
  type SavedMeetingView,
} from "./filters";

type Props = {
  currentFilters: MeetingFilters;
  initialViews: SavedMeetingView[];
};

export function SavedViewsClient({ currentFilters, initialViews }: Props) {
  const [views, setViews] = useState(initialViews);
  const [name, setName] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const activeFilters = useMemo(() => cleanedFilters(currentFilters), [currentFilters]);
  const canSave = Boolean(name.trim() && Object.keys(activeFilters).length);

  async function saveView() {
    if (!canSave || isSaving) {
      return;
    }

    setIsSaving(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/meeting-views`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          workspace_id: 1,
          name: name.trim(),
          filters: activeFilters,
        }),
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const view = (await response.json()) as SavedMeetingView;
      setViews((current) => [view, ...current]);
      setName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save view.");
    } finally {
      setIsSaving(false);
    }
  }

  async function deleteView(viewId: number) {
    setDeletingId(viewId);
    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/meeting-views/${viewId}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      setViews((current) => current.filter((view) => view.id !== viewId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete view.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="saved-views-block">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">Saved views</p>
          <h3>Reusable filters</h3>
        </div>
      </div>

      {views.length ? (
        <div className="saved-view-list">
          {views.map((view) => (
            <div className="saved-view-item" key={view.id}>
              <Link className="pill link-pill" href={meetingFiltersHref(view.filters)}>
                {view.name}
              </Link>
              <button
                className="button subtle danger compact-button"
                disabled={deletingId === view.id}
                onClick={() => void deleteView(view.id)}
                type="button"
              >
                {deletingId === view.id ? "Deleting..." : "Delete"}
              </button>
            </div>
          ))}
        </div>
      ) : (
        <p className="helper">No saved views yet.</p>
      )}

      <form
        className="saved-view-form"
        onSubmit={(event) => {
          event.preventDefault();
          void saveView();
        }}
      >
        <input
          className="input compact-input"
          onChange={(event) => setName(event.target.value)}
          placeholder="Name this filter"
          value={name}
        />
        <button className="button primary compact-button" disabled={!canSave || isSaving}>
          {isSaving ? "Saving..." : "Save view"}
        </button>
      </form>

      {error ? <div className="alert action-alert">{error}</div> : null}
    </div>
  );
}
