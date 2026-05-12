"use client";

import { useMemo, useState } from "react";
import { API_BASE_URL } from "../../lib/api";

export type CalendarAccount = {
  id: number;
  workspace_id: number;
  provider: string;
  account_email: string;
  display_name?: string | null;
  status: string;
  scopes: string[];
  provider_metadata: Record<string, unknown>;
  connected_at: string;
  last_sync_at?: string | null;
};

export type CalendarEvent = {
  id: number;
  workspace_id: number;
  calendar_account_id: number;
  external_event_id: string;
  title: string;
  starts_at?: string | null;
  ends_at?: string | null;
  organizer_email?: string | null;
  meeting_url?: string | null;
  location?: string | null;
  description?: string | null;
  attendees: Record<string, unknown>[];
  artifacts: Record<string, unknown>[];
  imported_meeting_id?: number | null;
};

type Props = {
  initialAccounts: CalendarAccount[];
  initialEvents: CalendarEvent[];
};

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    throw new Error(await response.text());
  }

  return response.json() as Promise<T>;
}

function toIsoDateTime(value: string) {
  return value ? new Date(value).toISOString() : null;
}

function formatDate(value?: string | null) {
  if (!value) {
    return "Date not set";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function providerLabel(provider: string) {
  const labels: Record<string, string> = {
    google: "Google Calendar",
    microsoft: "Microsoft Graph",
    outlook: "Outlook",
    local: "Local/manual",
  };
  return labels[provider] || provider;
}

export function CalendarClient({ initialAccounts, initialEvents }: Props) {
  const [accounts, setAccounts] = useState(initialAccounts);
  const [events, setEvents] = useState(initialEvents);
  const [provider, setProvider] = useState("local");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [accountId, setAccountId] = useState(
    initialAccounts.find((account) => account.status !== "disconnected")?.id.toString() ||
      "",
  );
  const [eventTitle, setEventTitle] = useState("");
  const [externalId, setExternalId] = useState("");
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const [meetingUrl, setMeetingUrl] = useState("");
  const [isSavingAccount, setIsSavingAccount] = useState(false);
  const [isSavingEvent, setIsSavingEvent] = useState(false);
  const [error, setError] = useState("");

  const connectedAccounts = useMemo(
    () => accounts.filter((account) => account.status !== "disconnected"),
    [accounts],
  );

  async function createAccount() {
    if (!email.trim() || isSavingAccount) {
      return;
    }

    setIsSavingAccount(true);
    setError("");
    try {
      const account = await postJson<CalendarAccount>("/calendar/accounts", {
        workspace_id: 1,
        provider,
        account_email: email.trim(),
        display_name: displayName.trim() || null,
        scopes: [],
        provider_metadata: { source: "manual_setup" },
      });
      setAccounts((current) => [account, ...current]);
      setAccountId(account.id.toString());
      setEmail("");
      setDisplayName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add calendar account.");
    } finally {
      setIsSavingAccount(false);
    }
  }

  async function disconnectAccount(nextAccountId: number) {
    setError("");
    try {
      const account = await postJson<CalendarAccount>(
        `/calendar/accounts/${nextAccountId}/disconnect`,
      );
      setAccounts((current) =>
        current.map((item) => (item.id === account.id ? account : item)),
      );
      if (accountId === account.id.toString()) {
        setAccountId("");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to disconnect account.");
    }
  }

  async function importEvent() {
    if (!accountId || !eventTitle.trim() || !externalId.trim() || isSavingEvent) {
      return;
    }

    setIsSavingEvent(true);
    setError("");
    try {
      const event = await postJson<CalendarEvent>("/calendar/events", {
        calendar_account_id: Number(accountId),
        external_event_id: externalId.trim(),
        title: eventTitle.trim(),
        starts_at: toIsoDateTime(startsAt),
        ends_at: toIsoDateTime(endsAt),
        meeting_url: meetingUrl.trim() || null,
        raw: { source: "manual_import" },
      });
      setEvents((current) => [event, ...current]);
      setEventTitle("");
      setExternalId("");
      setStartsAt("");
      setEndsAt("");
      setMeetingUrl("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to import calendar event.");
    } finally {
      setIsSavingEvent(false);
    }
  }

  return (
    <section className="calendar-layout">
      <div className="section-stack">
        {error ? <div className="alert">{error}</div> : null}

        <section className="panel">
          <div className="section-heading compact">
            <div>
              <p className="eyebrow">Accounts</p>
              <h3>Calendar accounts</h3>
            </div>
            <span className="pill">{connectedAccounts.length} connected</span>
          </div>

          <form
            className="calendar-form"
            onSubmit={(event) => {
              event.preventDefault();
              void createAccount();
            }}
          >
            <label className="field">
              <span className="label">Provider</span>
              <select
                className="input compact-input"
                onChange={(event) => setProvider(event.target.value)}
                value={provider}
              >
                <option value="local">Local/manual</option>
                <option value="google">Google Calendar</option>
                <option value="microsoft">Microsoft Graph</option>
                <option value="outlook">Outlook</option>
              </select>
            </label>
            <label className="field">
              <span className="label">Account email</span>
              <input
                className="input compact-input"
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                value={email}
              />
            </label>
            <label className="field">
              <span className="label">Display name</span>
              <input
                className="input compact-input"
                onChange={(event) => setDisplayName(event.target.value)}
                placeholder="Work calendar"
                value={displayName}
              />
            </label>
            <button
              className="button primary compact-button"
              disabled={!email.trim() || isSavingAccount}
            >
              {isSavingAccount ? "Adding..." : "Add account"}
            </button>
          </form>

          {accounts.length ? (
            <div className="calendar-account-list">
              {accounts.map((account) => (
                <article className="calendar-account" key={account.id}>
                  <div>
                    <strong>{account.display_name || account.account_email}</strong>
                    <p className="helper">
                      {providerLabel(account.provider)} / {account.account_email}
                    </p>
                  </div>
                  <div className="actions inline-actions">
                    <span className={`status ${account.status}`}>
                      {account.status}
                    </span>
                    {account.status !== "disconnected" ? (
                      <button
                        className="button subtle danger compact-button"
                        onClick={() => void disconnectAccount(account.id)}
                        type="button"
                      >
                        Disconnect
                      </button>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="helper">No calendar accounts have been added yet.</p>
          )}
        </section>

        <section className="panel">
          <div className="section-heading compact">
            <div>
              <p className="eyebrow">Import foundation</p>
              <h3>Calendar events</h3>
            </div>
            <span className="pill">{events.length} imported</span>
          </div>

          <form
            className="calendar-form"
            onSubmit={(event) => {
              event.preventDefault();
              void importEvent();
            }}
          >
            <label className="field">
              <span className="label">Account</span>
              <select
                className="input compact-input"
                disabled={!connectedAccounts.length}
                onChange={(event) => setAccountId(event.target.value)}
                value={accountId}
              >
                <option value="">Choose account</option>
                {connectedAccounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.display_name || account.account_email}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span className="label">Event title</span>
              <input
                className="input compact-input"
                onChange={(event) => setEventTitle(event.target.value)}
                placeholder="Customer onboarding sync"
                value={eventTitle}
              />
            </label>
            <label className="field">
              <span className="label">External event ID</span>
              <input
                className="input compact-input"
                onChange={(event) => setExternalId(event.target.value)}
                placeholder="provider-event-id"
                value={externalId}
              />
            </label>
            <label className="field">
              <span className="label">Starts</span>
              <input
                className="input compact-input"
                onChange={(event) => setStartsAt(event.target.value)}
                type="datetime-local"
                value={startsAt}
              />
            </label>
            <label className="field">
              <span className="label">Ends</span>
              <input
                className="input compact-input"
                onChange={(event) => setEndsAt(event.target.value)}
                type="datetime-local"
                value={endsAt}
              />
            </label>
            <label className="field">
              <span className="label">Meeting URL</span>
              <input
                className="input compact-input"
                onChange={(event) => setMeetingUrl(event.target.value)}
                placeholder="https://meet.google.com/..."
                value={meetingUrl}
              />
            </label>
            <button
              className="button primary compact-button"
              disabled={
                !accountId || !eventTitle.trim() || !externalId.trim() || isSavingEvent
              }
            >
              {isSavingEvent ? "Importing..." : "Import event"}
            </button>
          </form>

          {events.length ? (
            <div className="calendar-event-list">
              {events.map((event) => (
                <article className="calendar-event" key={event.id}>
                  <div>
                    <strong>{event.title}</strong>
                    <p className="helper">{formatDate(event.starts_at)}</p>
                  </div>
                  <div className="meta-row">
                    {event.meeting_url ? (
                      <a className="pill link-pill" href={event.meeting_url}>
                        Meeting link
                      </a>
                    ) : null}
                    {event.imported_meeting_id ? (
                      <span className="status completed">Meeting created</span>
                    ) : (
                      <span className="status uploaded">Event only</span>
                    )}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="helper">Imported calendar events will appear here.</p>
          )}
        </section>
      </div>

      <aside className="panel inspector-panel">
        <div className="section-heading compact">
          <div>
            <p className="eyebrow">External API readiness</p>
            <h3>What you will need</h3>
          </div>
        </div>
        <ul className="check-list">
          <li>Google Cloud or Microsoft Entra app registration</li>
          <li>OAuth client ID and client secret</li>
          <li>Redirect URL for this backend</li>
          <li>Calendar read scopes approved for your account</li>
          <li>Test calendar account with meeting links and artifacts</li>
        </ul>
        <p className="footer-note">
          This page does not call external calendar APIs yet. It establishes the
          storage and API shape that provider sync will use.
        </p>
      </aside>
    </section>
  );
}
