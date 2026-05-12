"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { API_BASE_URL } from "../../lib/api";

export type ActionItem = {
  id: number;
  meeting_id: number;
  meeting_title: string;
  task: string;
  owner: string | null;
  due_date: string | null;
  priority: string;
  status: string;
  evidence: string;
  created_at: string;
  archived_at: string | null;
};

export type MeetingOption = {
  id: number;
  title: string;
};

type Filter = "all" | "open" | "done" | "archived";
type DueFilter = "all" | "overdue" | "today" | "upcoming" | "no-date";
type SortMode = "due-asc" | "due-desc" | "created-desc";

type ActionItemPatch = {
  task?: string;
  owner?: string | null;
  due_date?: string | null;
  priority?: string;
  status?: string;
  evidence?: string;
};

type ActionItemCreate = {
  meeting_id: number;
  task: string;
  owner?: string | null;
  due_date?: string | null;
  priority: string;
  evidence: string;
};

type ActionItemDraft = {
  task: string;
  owner: string;
  due_date: string;
  priority: string;
  evidence: string;
};

type Props = {
  initialItems: ActionItem[];
  meetings: MeetingOption[];
};

const ALL_OWNERS = "__all__";
const UNASSIGNED = "__unassigned__";

function parseDueDate(value: string | null) {
  if (!value) {
    return null;
  }

  const trimmed = value.trim();
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(trimmed);
  if (match) {
    return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  }

  const parsed = new Date(trimmed);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function startOfToday() {
  const today = new Date();
  return new Date(today.getFullYear(), today.getMonth(), today.getDate());
}

function dateKey(date: Date) {
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
}

function isOverdue(item: ActionItem) {
  const dueDate = parseDueDate(item.due_date);
  return Boolean(
    !item.archived_at && dueDate && item.status !== "done" && dueDate < startOfToday(),
  );
}

async function patchActionItem(id: number, body: ActionItemPatch) {
  const response = await fetch(`${API_BASE_URL}/action-items/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }
}

async function createActionItem(body: ActionItemCreate) {
  const response = await fetch(`${API_BASE_URL}/action-items`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<ActionItem>;
}

async function postActionItemState(id: number, action: "archive" | "restore") {
  const response = await fetch(`${API_BASE_URL}/action-items/${id}/${action}`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<ActionItem>;
}

function emptyDraft(meetingId = "") {
  return {
    meeting_id: meetingId,
    task: "",
    owner: "",
    due_date: "",
    priority: "medium",
    evidence: "",
  };
}

export function ActionItemsClient({ initialItems, meetings }: Props) {
  const [items, setItems] = useState(initialItems);
  const [filter, setFilter] = useState<Filter>("open");
  const [ownerFilter, setOwnerFilter] = useState(ALL_OWNERS);
  const [dueFilter, setDueFilter] = useState<DueFilter>("all");
  const [sortMode, setSortMode] = useState<SortMode>("due-asc");
  const [savingId, setSavingId] = useState<number | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [createDraft, setCreateDraft] = useState(emptyDraft(meetings[0]?.id.toString()));
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<ActionItemDraft | null>(null);
  const [error, setError] = useState("");

  const filteredItems = useMemo(() => {
    const today = startOfToday();
    const nextItems = items.filter((item) => {
      const isArchived = Boolean(item.archived_at);

      if (filter === "archived") {
        if (!isArchived) {
          return false;
        }
      } else if (isArchived) {
        return false;
      }

      if (filter !== "all" && filter !== "archived" && item.status !== filter) {
        return false;
      }

      if (ownerFilter === UNASSIGNED && item.owner) {
        return false;
      }

      if (
        ownerFilter !== ALL_OWNERS &&
        ownerFilter !== UNASSIGNED &&
        item.owner !== ownerFilter
      ) {
        return false;
      }

      const dueDate = parseDueDate(item.due_date);
      if (dueFilter === "no-date") {
        return !dueDate;
      }
      if (dueFilter === "overdue") {
        return isOverdue(item);
      }
      if (dueFilter === "today") {
        return Boolean(dueDate && dateKey(dueDate) === dateKey(today));
      }
      if (dueFilter === "upcoming") {
        return Boolean(dueDate && dueDate >= today);
      }

      return true;
    });

    return [...nextItems].sort((left, right) => {
      if (sortMode === "created-desc") {
        return (
          new Date(right.created_at).getTime() - new Date(left.created_at).getTime()
        );
      }

      const leftDue = parseDueDate(left.due_date)?.getTime();
      const rightDue = parseDueDate(right.due_date)?.getTime();

      if (leftDue === undefined && rightDue === undefined) {
        return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
      }
      if (leftDue === undefined) {
        return 1;
      }
      if (rightDue === undefined) {
        return -1;
      }

      return sortMode === "due-desc" ? rightDue - leftDue : leftDue - rightDue;
    });
  }, [dueFilter, filter, items, ownerFilter, sortMode]);

  const totals = useMemo(() => {
    const activeItems = items.filter((item) => !item.archived_at);
    const open = activeItems.filter((item) => item.status === "open").length;
    const done = activeItems.filter((item) => item.status === "done").length;
    const overdue = items.filter(isOverdue).length;
    return { open, done, overdue };
  }, [items]);

  const owners = useMemo(() => {
    return Array.from(
      new Set(
        items
          .map((item) => item.owner)
          .filter((owner): owner is string => Boolean(owner)),
      ),
    ).sort((left, right) => left.localeCompare(right));
  }, [items]);

  async function setStatus(item: ActionItem, status: "open" | "done") {
    if (item.archived_at) {
      return;
    }

    setSavingId(item.id);
    setError("");
    const previous = items;
    setItems((current) =>
      current.map((currentItem) =>
        currentItem.id === item.id ? { ...currentItem, status } : currentItem,
      ),
    );

    try {
      await patchActionItem(item.id, { status });
    } catch (err) {
      setItems(previous);
      setError(err instanceof Error ? err.message : "Unable to update action item.");
    } finally {
      setSavingId(null);
    }
  }

  async function setArchiveState(item: ActionItem, archived: boolean) {
    setSavingId(item.id);
    setError("");
    const previous = items;
    const optimisticArchiveDate = archived ? new Date().toISOString() : null;

    setItems((current) =>
      current.map((currentItem) =>
        currentItem.id === item.id
          ? { ...currentItem, archived_at: optimisticArchiveDate }
          : currentItem,
      ),
    );

    try {
      const nextItem = await postActionItemState(
        item.id,
        archived ? "archive" : "restore",
      );
      setItems((current) =>
        current.map((currentItem) =>
          currentItem.id === item.id ? nextItem : currentItem,
        ),
      );
      if (editingId === item.id) {
        cancelEdit();
      }
    } catch (err) {
      setItems(previous);
      setError(err instanceof Error ? err.message : "Unable to update archive state.");
    } finally {
      setSavingId(null);
    }
  }

  function startEdit(item: ActionItem) {
    setEditingId(item.id);
    setError("");
    setDraft({
      task: item.task,
      owner: item.owner || "",
      due_date: item.due_date || "",
      priority: item.priority || "medium",
      evidence: item.evidence || "",
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setDraft(null);
  }

  async function saveEdit(item: ActionItem) {
    if (!draft || !draft.task.trim()) {
      setError("Task is required.");
      return;
    }

    const patch: ActionItemPatch = {
      task: draft.task.trim(),
      owner: draft.owner.trim() || null,
      due_date: draft.due_date.trim() || null,
      priority: draft.priority,
      evidence: draft.evidence.trim(),
    };
    const previous = items;

    setSavingId(item.id);
    setError("");
    setItems((current) =>
      current.map((currentItem) =>
        currentItem.id === item.id ? { ...currentItem, ...patch } : currentItem,
      ),
    );

    try {
      await patchActionItem(item.id, patch);
      cancelEdit();
    } catch (err) {
      setItems(previous);
      setError(err instanceof Error ? err.message : "Unable to save action item.");
    } finally {
      setSavingId(null);
    }
  }

  function updateDraft(field: keyof ActionItemDraft, value: string) {
    setDraft((current) => (current ? { ...current, [field]: value } : current));
  }

  function updateCreateDraft(field: keyof typeof createDraft, value: string) {
    setCreateDraft((current) => ({ ...current, [field]: value }));
  }

  async function submitCreate() {
    if (!meetings.length) {
      setError("Create a meeting before adding manual action items.");
      return;
    }
    if (!createDraft.meeting_id) {
      setError("Choose a meeting for this action item.");
      return;
    }
    if (!createDraft.task.trim()) {
      setError("Task is required.");
      return;
    }

    setIsCreating(true);
    setError("");

    try {
      const item = await createActionItem({
        meeting_id: Number(createDraft.meeting_id),
        task: createDraft.task.trim(),
        owner: createDraft.owner.trim() || null,
        due_date: createDraft.due_date.trim() || null,
        priority: createDraft.priority,
        evidence: createDraft.evidence.trim(),
      });
      setItems((current) => [item, ...current]);
      setCreateDraft(emptyDraft(createDraft.meeting_id));
      setFilter("open");
      setSortMode("created-desc");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create action item.");
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <>
      <section className="grid three stat-grid" aria-label="Action item totals">
        <div className="card metric accent-blue">
          <span className="metric-label">Open</span>
          <strong className="metric-value">{totals.open}</strong>
          <span className="helper">Items still waiting on follow-up.</span>
        </div>
        <div className="card metric accent-green">
          <span className="metric-label">Overdue</span>
          <strong className="metric-value">{totals.overdue}</strong>
          <span className="helper">Open items past their due date.</span>
        </div>
        <div className="card metric accent-amber">
          <span className="metric-label">Done</span>
          <strong className="metric-value">{totals.done}</strong>
          <span className="helper">Completed follow-up work.</span>
        </div>
      </section>

      <section className="panel list-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Follow-up</p>
            <h3>Action workspace</h3>
          </div>
          <div className="segmented-control" aria-label="Filter action items">
            {(["open", "all", "done", "archived"] as Filter[]).map((nextFilter) => (
              <button
                className={filter === nextFilter ? "active" : ""}
                key={nextFilter}
                onClick={() => setFilter(nextFilter)}
                type="button"
              >
                {nextFilter}
              </button>
            ))}
          </div>
        </div>

        <form
          className="create-action-form"
          onSubmit={(event) => {
            event.preventDefault();
            void submitCreate();
          }}
        >
          <div className="section-heading compact">
            <div>
              <p className="eyebrow">Manual task</p>
              <h3>Add action item</h3>
            </div>
          </div>

          <label className="field">
            <span className="label">Task</span>
            <textarea
              className="textarea compact"
              onChange={(event) => updateCreateDraft("task", event.target.value)}
              placeholder="Add a follow-up task that was missed in the meeting notes."
              value={createDraft.task}
            />
          </label>

          <div className="form-grid">
            <label className="field">
              <span className="label">Meeting</span>
              <select
                className="input"
                disabled={!meetings.length}
                onChange={(event) => updateCreateDraft("meeting_id", event.target.value)}
                value={createDraft.meeting_id}
              >
                {meetings.length ? null : <option value="">No meetings yet</option>}
                {meetings.map((meeting) => (
                  <option key={meeting.id} value={meeting.id}>
                    {meeting.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span className="label">Owner</span>
              <input
                className="input"
                onChange={(event) => updateCreateDraft("owner", event.target.value)}
                placeholder="Unassigned"
                value={createDraft.owner}
              />
            </label>
            <label className="field">
              <span className="label">Due date</span>
              <input
                className="input"
                onChange={(event) => updateCreateDraft("due_date", event.target.value)}
                placeholder="YYYY-MM-DD"
                value={createDraft.due_date}
              />
            </label>
          </div>

          <div className="form-grid two-plus-one">
            <label className="field">
              <span className="label">Priority</span>
              <select
                className="input"
                onChange={(event) => updateCreateDraft("priority", event.target.value)}
                value={createDraft.priority}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </label>
            <label className="field wide-field">
              <span className="label">Evidence</span>
              <input
                className="input"
                onChange={(event) => updateCreateDraft("evidence", event.target.value)}
                placeholder="Optional source context or note"
                value={createDraft.evidence}
              />
            </label>
          </div>

          <div className="actions inline-actions">
            <button
              className="button primary"
              disabled={isCreating || !meetings.length}
              type="submit"
            >
              {isCreating ? "Adding..." : "Add action item"}
            </button>
          </div>
        </form>

        <div className="filter-bar" aria-label="Action item filters">
          <label className="filter-field">
            <span className="label">Owner</span>
            <select
              className="input compact-input"
              onChange={(event) => setOwnerFilter(event.target.value)}
              value={ownerFilter}
            >
              <option value={ALL_OWNERS}>All owners</option>
              <option value={UNASSIGNED}>Unassigned</option>
              {owners.map((owner) => (
                <option key={owner} value={owner}>
                  {owner}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            <span className="label">Due</span>
            <select
              className="input compact-input"
              onChange={(event) => setDueFilter(event.target.value as DueFilter)}
              value={dueFilter}
            >
              <option value="all">All due dates</option>
              <option value="overdue">Overdue</option>
              <option value="today">Due today</option>
              <option value="upcoming">Upcoming</option>
              <option value="no-date">No due date</option>
            </select>
          </label>
          <label className="filter-field">
            <span className="label">Sort</span>
            <select
              className="input compact-input"
              onChange={(event) => setSortMode(event.target.value as SortMode)}
              value={sortMode}
            >
              <option value="due-asc">Due soonest</option>
              <option value="due-desc">Due latest</option>
              <option value="created-desc">Newest created</option>
            </select>
          </label>
        </div>

        {error ? <div className="alert action-alert">{error}</div> : null}

        {filteredItems.length === 0 ? (
          <div className="empty">
            <div className="empty-inner">
              <h3>No action items here</h3>
              <p className="helper">
                {filter === "archived"
                  ? "Archived action items will appear here after you remove them from active follow-up."
                  : "Process a meeting with follow-up tasks or switch filters to see completed work."}
              </p>
              <Link className="button primary" href="/meetings">
                View meetings
              </Link>
            </div>
          </div>
        ) : (
          <ul className="action-list">
            {filteredItems.map((item) => {
              const isDone = item.status === "done";
              const isArchived = Boolean(item.archived_at);
              const isEditing = editingId === item.id && draft;
              const overdue = isOverdue(item);
              return (
                <li
                  className={`action-row ${isDone ? "done" : ""} ${
                    isArchived ? "archived" : ""
                  } ${
                    overdue ? "overdue" : ""
                  }`}
                  key={item.id}
                >
                  <button
                    aria-label={isDone ? "Mark open" : "Mark done"}
                    className="check-button"
                    disabled={savingId === item.id || isArchived}
                    onClick={() => void setStatus(item, isDone ? "open" : "done")}
                    type="button"
                  >
                    <span />
                  </button>

                  <div className="action-content">
                    {isEditing ? (
                      <div className="action-edit-form">
                        <label className="field">
                          <span className="label">Task</span>
                          <textarea
                            className="textarea compact"
                            onChange={(event) => updateDraft("task", event.target.value)}
                            value={draft.task}
                          />
                        </label>

                        <div className="form-grid">
                          <label className="field">
                            <span className="label">Owner</span>
                            <input
                              className="input"
                              onChange={(event) => updateDraft("owner", event.target.value)}
                              placeholder="Unassigned"
                              value={draft.owner}
                            />
                          </label>
                          <label className="field">
                            <span className="label">Due date</span>
                            <input
                              className="input"
                              onChange={(event) =>
                                updateDraft("due_date", event.target.value)
                              }
                              placeholder="YYYY-MM-DD"
                              value={draft.due_date}
                            />
                          </label>
                          <label className="field">
                            <span className="label">Priority</span>
                            <select
                              className="input"
                              onChange={(event) =>
                                updateDraft("priority", event.target.value)
                              }
                              value={draft.priority}
                            >
                              <option value="low">Low</option>
                              <option value="medium">Medium</option>
                              <option value="high">High</option>
                            </select>
                          </label>
                        </div>

                        <label className="field">
                          <span className="label">Evidence</span>
                          <textarea
                            className="textarea compact"
                            onChange={(event) =>
                              updateDraft("evidence", event.target.value)
                            }
                            value={draft.evidence}
                          />
                        </label>

                        <div className="actions inline-actions">
                          <button
                            className="button primary"
                            disabled={savingId === item.id}
                            onClick={() => void saveEdit(item)}
                            type="button"
                          >
                            {savingId === item.id ? "Saving..." : "Save"}
                          </button>
                          <button
                            className="button"
                            disabled={savingId === item.id}
                            onClick={cancelEdit}
                            type="button"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="action-title-row">
                          <strong>{item.task}</strong>
                          <span className={`status ${isArchived ? "archived" : item.status}`}>
                            {isArchived ? "archived" : item.status}
                          </span>
                        </div>
                        <div className="meta-row">
                          <Link
                            className="pill link-pill"
                            href={`/meetings/${item.meeting_id}`}
                          >
                            {item.meeting_title}
                          </Link>
                          <span className="pill">{item.owner || "Unassigned"}</span>
                          <span className="pill">{item.priority || "medium"}</span>
                          {overdue ? <span className="pill overdue-pill">Overdue</span> : null}
                          {item.due_date ? (
                            <span className="pill">{item.due_date}</span>
                          ) : null}
                        </div>
                        {item.evidence ? <p className="helper">{item.evidence}</p> : null}
                        <div className="actions inline-actions">
                          {isArchived ? (
                            <button
                              className="button subtle"
                              disabled={savingId === item.id}
                              onClick={() => void setArchiveState(item, false)}
                              type="button"
                            >
                              {savingId === item.id ? "Restoring..." : "Restore"}
                            </button>
                          ) : (
                            <>
                              <button
                                className="button subtle"
                                onClick={() => startEdit(item)}
                                type="button"
                              >
                                Edit
                              </button>
                              <button
                                className="button subtle danger"
                                disabled={savingId === item.id}
                                onClick={() => void setArchiveState(item, true)}
                                type="button"
                              >
                                {savingId === item.id ? "Archiving..." : "Archive"}
                              </button>
                            </>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </>
  );
}
