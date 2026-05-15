"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
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

export type CalendarProviderStatus = {
  provider: string;
  label: string;
  configured: boolean;
  client_id_configured: boolean;
  client_secret_configured: boolean;
  redirect_uri: string;
  scopes: string[];
  auth_url: string;
  events_url: string;
};

type CalendarBulkMeetingResult = {
  requested: number;
  eligible: number;
  created: number;
  skipped_existing: number;
  skipped_missing_link: number;
  skipped_missing_event: number;
  events: CalendarEvent[];
};

type Props = {
  initialAccounts: CalendarAccount[];
  initialEvents: CalendarEvent[];
  providerStatuses: CalendarProviderStatus[];
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

async function fetchCalendarEvents(filters: {
  accountId: string;
  provider: string;
  query: string;
  importStatus: string;
  linkStatus: string;
  dateFrom: string;
  dateTo: string;
}) {
  const params = new URLSearchParams({ workspace_id: "1", limit: "100" });
  if (filters.accountId) {
    params.set("calendar_account_id", filters.accountId);
  }
  if (filters.provider !== "all") {
    params.set("provider", filters.provider);
  }
  if (filters.query.trim()) {
    params.set("q", filters.query.trim());
  }
  if (filters.importStatus !== "all") {
    params.set("import_status", filters.importStatus);
  }
  if (filters.linkStatus !== "all") {
    params.set("has_meeting_url", filters.linkStatus === "has_link" ? "true" : "false");
  }
  if (filters.dateFrom) {
    params.set("date_from", new Date(filters.dateFrom).toISOString());
  }
  if (filters.dateTo) {
    params.set("date_to", new Date(filters.dateTo).toISOString());
  }

  const response = await fetch(`${API_BASE_URL}/calendar/events?${params.toString()}`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json() as Promise<CalendarEvent[]>;
}

export function CalendarClient({
  initialAccounts,
  initialEvents,
  providerStatuses,
}: Props) {
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
  const [syncingAccountId, setSyncingAccountId] = useState<number | null>(null);
  const [creatingMeetingId, setCreatingMeetingId] = useState<number | null>(null);
  const [isBulkCreating, setIsBulkCreating] = useState(false);
  const [bulkRequireMeetingLink, setBulkRequireMeetingLink] = useState(true);
  const [autoSyncEnabled, setAutoSyncEnabled] = useState(true);
  const [isAutoSyncing, setIsAutoSyncing] = useState(false);
  const [showSyncSettings, setShowSyncSettings] = useState(false);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [showManualImport, setShowManualImport] = useState(false);
  const [syncDaysBack, setSyncDaysBack] = useState(7);
  const [syncDaysForward, setSyncDaysForward] = useState(30);
  const [syncMaxResults, setSyncMaxResults] = useState(100);
  const [syncMaxPages, setSyncMaxPages] = useState(3);
  const [eventAccountFilter, setEventAccountFilter] = useState("");
  const [eventProviderFilter, setEventProviderFilter] = useState("all");
  const [eventQuery, setEventQuery] = useState("");
  const [eventImportStatus, setEventImportStatus] = useState("all");
  const [eventLinkStatus, setEventLinkStatus] = useState("all");
  const [eventDateFrom, setEventDateFrom] = useState("");
  const [eventDateTo, setEventDateTo] = useState("");
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);
  const [syncMessage, setSyncMessage] = useState("");
  const [error, setError] = useState("");

  const connectedAccounts = useMemo(
    () => accounts.filter((account) => account.status !== "disconnected"),
    [accounts],
  );
  const oauthAccounts = useMemo(
    () =>
      connectedAccounts.filter(
        (account) => account.provider !== "local" && account.scopes.length > 0,
      ),
    [connectedAccounts],
  );
  const accountById = useMemo(
    () => new Map(accounts.map((account) => [account.id, account])),
    [accounts],
  );
  const activeEventFilters = [
    eventAccountFilter,
    eventProviderFilter !== "all" ? eventProviderFilter : "",
    eventQuery.trim(),
    eventImportStatus !== "all" ? eventImportStatus : "",
    eventLinkStatus !== "all" ? eventLinkStatus : "",
    eventDateFrom,
    eventDateTo,
  ].filter(Boolean).length;
  const bulkCandidateCount = events.filter((event) => !event.imported_meeting_id).length;

  const refreshEvents = useCallback(async (overrides: Partial<{
    accountId: string;
    provider: string;
    query: string;
    importStatus: string;
    linkStatus: string;
    dateFrom: string;
    dateTo: string;
  }> = {}) => {
    setIsLoadingEvents(true);
    setError("");
    try {
      const nextEvents = await fetchCalendarEvents({
        accountId: overrides.accountId ?? eventAccountFilter,
        provider: overrides.provider ?? eventProviderFilter,
        query: overrides.query ?? eventQuery,
        importStatus: overrides.importStatus ?? eventImportStatus,
        linkStatus: overrides.linkStatus ?? eventLinkStatus,
        dateFrom: overrides.dateFrom ?? eventDateFrom,
        dateTo: overrides.dateTo ?? eventDateTo,
      });
      setEvents(nextEvents);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load calendar events.");
    } finally {
      setIsLoadingEvents(false);
    }
  }, [
    eventAccountFilter,
    eventProviderFilter,
    eventQuery,
    eventImportStatus,
    eventLinkStatus,
    eventDateFrom,
    eventDateTo,
  ]);

  function upsertEvent(nextEvent: CalendarEvent) {
    setEvents((current) => {
      const existing = current.find((item) => item.id === nextEvent.id);
      if (existing) {
        return current.map((item) => (item.id === nextEvent.id ? nextEvent : item));
      }
      return [nextEvent, ...current];
    });
  }

  function upsertEvents(nextEvents: CalendarEvent[]) {
    setEvents((current) => {
      const nextById = new Map(nextEvents.map((event) => [event.id, event]));
      const updated = current.map((event) => nextById.get(event.id) || event);
      const existingIds = new Set(updated.map((event) => event.id));
      return [
        ...nextEvents.filter((event) => !existingIds.has(event.id)),
        ...updated,
      ];
    });
  }

  const syncSettingsPayload = useCallback(() => {
    return {
      days_back: Math.max(0, Math.min(Number(syncDaysBack) || 0, 365)),
      days_forward: Math.max(0, Math.min(Number(syncDaysForward) || 0, 365)),
      max_results: Math.max(1, Math.min(Number(syncMaxResults) || 1, 1000)),
      max_pages: Math.max(1, Math.min(Number(syncMaxPages) || 1, 20)),
    };
  }, [syncDaysBack, syncDaysForward, syncMaxResults, syncMaxPages]);

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

  const syncAccount = useCallback(async (
    nextAccountId: number,
    options: { quiet?: boolean } = {},
  ) => {
    setSyncingAccountId(nextAccountId);
    if (!options.quiet) {
      setSyncMessage("");
    }
    setError("");
    try {
      const result = await postJson<{
        status: string;
        message: string;
        events_imported: number;
        events_updated?: number;
        token_refreshed?: boolean;
        events_scanned?: number;
      }>(`/calendar/accounts/${nextAccountId}/sync`, syncSettingsPayload());
      if (!options.quiet || result.status === "synced") {
        setSyncMessage(
          `${options.quiet ? "auto-sync" : result.status}: ${result.message}${
            typeof result.events_scanned === "number"
              ? ` Scanned ${result.events_scanned} event(s).`
              : ""
          }${
            result.token_refreshed ? " Token refreshed." : ""
          }`,
        );
      }
      if (result.status === "synced") {
        await refreshEvents();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sync account.");
    } finally {
      setSyncingAccountId(null);
    }
  }, [refreshEvents, syncSettingsPayload]);

  useEffect(() => {
    if (!autoSyncEnabled || !oauthAccounts.length) {
      return;
    }

    let cancelled = false;

    async function syncOAuthAccounts() {
      if (cancelled) {
        return;
      }
      setIsAutoSyncing(true);
      try {
        for (const account of oauthAccounts) {
          if (cancelled) {
            return;
          }
          await syncAccount(account.id, { quiet: true });
        }
      } finally {
        if (!cancelled) {
          setIsAutoSyncing(false);
        }
      }
    }

    const initialSync = window.setTimeout(() => {
      void syncOAuthAccounts();
    }, 1500);
    const interval = window.setInterval(() => {
      void syncOAuthAccounts();
    }, 5 * 60 * 1000);

    return () => {
      cancelled = true;
      window.clearTimeout(initialSync);
      window.clearInterval(interval);
    };
  }, [autoSyncEnabled, oauthAccounts, syncAccount]);

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
      if (activeEventFilters) {
        await refreshEvents();
      } else {
        upsertEvent(event);
      }
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

  async function createMeetingFromEvent(eventId: number) {
    setCreatingMeetingId(eventId);
    setError("");
    try {
      const event = await postJson<CalendarEvent>(
        `/calendar/events/${eventId}/create-meeting`,
        { tags: ["calendar"] },
      );
      if (activeEventFilters) {
        await refreshEvents();
      } else {
        upsertEvent(event);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create meeting.");
    } finally {
      setCreatingMeetingId(null);
    }
  }

  async function createMeetingsForShownEvents() {
    if (!events.length || isBulkCreating) {
      return;
    }

    setIsBulkCreating(true);
    setError("");
    setSyncMessage("");
    try {
      const result = await postJson<CalendarBulkMeetingResult>(
        "/calendar/events/create-meetings",
        {
          event_ids: events.map((event) => event.id),
          tags: ["calendar"],
          require_meeting_url: bulkRequireMeetingLink,
        },
      );
      setSyncMessage(
        `automation: Created ${result.created} meeting(s). Skipped ${result.skipped_existing} existing, ${result.skipped_missing_link} without meeting links, and ${result.skipped_missing_event} missing event(s).`,
      );
      if (activeEventFilters) {
        await refreshEvents();
      } else {
        upsertEvents(result.events);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create meetings.");
    } finally {
      setIsBulkCreating(false);
    }
  }

  return (
    <section className="calendar-layout">
      <div className="section-stack">
        {error ? <div className="alert">{error}</div> : null}
        {syncMessage ? <div className="alert muted-alert">{syncMessage}</div> : null}

        <section className="panel">
          <div className="section-heading compact">
            <div>
              <p className="eyebrow">Accounts</p>
              <h3>Calendar accounts</h3>
            </div>
            <div className="meta-row">
              <span className="pill">{connectedAccounts.length} connected</span>
              {oauthAccounts.length ? (
                <span className={`status ${isAutoSyncing ? "uploaded" : "completed"}`}>
                  {isAutoSyncing ? "Syncing" : "Auto-sync on"}
                </span>
              ) : null}
            </div>
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
                      <>
                        <button
                          className="button subtle compact-button"
                          disabled={syncingAccountId === account.id}
                          onClick={() => void syncAccount(account.id)}
                          type="button"
                        >
                          {syncingAccountId === account.id ? "Syncing..." : "Sync"}
                        </button>
                        <button
                          className="button subtle danger compact-button"
                          onClick={() => void disconnectAccount(account.id)}
                          type="button"
                        >
                          Disconnect
                        </button>
                      </>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="helper">No calendar accounts have been added yet.</p>
          )}

          {oauthAccounts.length ? (
            <div className="calendar-automation-panel compact-automation">
              <div>
                <p className="eyebrow">Sync</p>
                <strong>OAuth calendars sync every 5 minutes while this page is open.</strong>
              </div>
              <label className="toggle-field">
                <input
                  checked={autoSyncEnabled}
                  onChange={(event) => setAutoSyncEnabled(event.target.checked)}
                  type="checkbox"
                />
                <span>Auto-sync</span>
              </label>
              <button
                className="button subtle compact-button"
                onClick={() => setShowSyncSettings((current) => !current)}
                type="button"
              >
                {showSyncSettings ? "Hide settings" : "Sync settings"}
              </button>
            </div>
          ) : null}

          {showSyncSettings ? (
            <div className="calendar-sync-controls">
              <label className="field">
                <span className="label">Days back</span>
                <input
                  className="input compact-input"
                  max={365}
                  min={0}
                  onChange={(event) => setSyncDaysBack(Number(event.target.value))}
                  type="number"
                  value={syncDaysBack}
                />
              </label>
              <label className="field">
                <span className="label">Days forward</span>
                <input
                  className="input compact-input"
                  max={365}
                  min={0}
                  onChange={(event) => setSyncDaysForward(Number(event.target.value))}
                  type="number"
                  value={syncDaysForward}
                />
              </label>
              <label className="field">
                <span className="label">Max events</span>
                <input
                  className="input compact-input"
                  max={1000}
                  min={1}
                  onChange={(event) => setSyncMaxResults(Number(event.target.value))}
                  type="number"
                  value={syncMaxResults}
                />
              </label>
              <label className="field">
                <span className="label">Max pages</span>
                <input
                  className="input compact-input"
                  max={20}
                  min={1}
                  onChange={(event) => setSyncMaxPages(Number(event.target.value))}
                  type="number"
                  value={syncMaxPages}
                />
              </label>
            </div>
          ) : null}
        </section>

        <section className="panel">
          <div className="section-heading compact">
            <div>
              <p className="eyebrow">Import foundation</p>
              <h3>Calendar events</h3>
            </div>
            <div className="meta-row">
              {activeEventFilters ? (
                <span className="pill">{activeEventFilters} filter(s)</span>
              ) : null}
              <span className="pill">{events.length} shown</span>
            </div>
          </div>

          <form
            className="calendar-filter-form compact-calendar-filters"
            onSubmit={(event) => {
              event.preventDefault();
              void refreshEvents();
            }}
          >
            <label className="field">
              <span className="label">Search</span>
              <input
                className="input compact-input"
                onChange={(event) => setEventQuery(event.target.value)}
                placeholder="Title, organizer, location"
                value={eventQuery}
              />
            </label>
            <label className="field">
              <span className="label">Import state</span>
              <select
                className="input compact-input"
                onChange={(event) => setEventImportStatus(event.target.value)}
                value={eventImportStatus}
              >
                <option value="all">All events</option>
                <option value="not_imported">Needs meeting</option>
                <option value="imported">Meeting created</option>
              </select>
            </label>
            <div className="calendar-filter-actions">
              <button className="button primary compact-button" disabled={isLoadingEvents}>
                {isLoadingEvents ? "Loading..." : "Apply filters"}
              </button>
              <button
                className="button subtle compact-button"
                onClick={() => setShowAdvancedFilters((current) => !current)}
                type="button"
              >
                {showAdvancedFilters ? "Hide advanced" : "Advanced"}
              </button>
              <button
                className="button subtle compact-button"
                disabled={isLoadingEvents || !activeEventFilters}
                onClick={() => {
                  setEventAccountFilter("");
                  setEventProviderFilter("all");
                  setEventQuery("");
                  setEventImportStatus("all");
                  setEventLinkStatus("all");
                  setEventDateFrom("");
                  setEventDateTo("");
                  void refreshEvents({
                    accountId: "",
                    provider: "all",
                    query: "",
                    importStatus: "all",
                    linkStatus: "all",
                    dateFrom: "",
                    dateTo: "",
                  });
                }}
                type="button"
              >
                Reset
              </button>
            </div>
            {showAdvancedFilters ? (
              <>
                <label className="field">
                  <span className="label">Account</span>
                  <select
                    className="input compact-input"
                    onChange={(event) => setEventAccountFilter(event.target.value)}
                    value={eventAccountFilter}
                  >
                    <option value="">All accounts</option>
                    {accounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.display_name || account.account_email}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span className="label">Provider</span>
                  <select
                    className="input compact-input"
                    onChange={(event) => setEventProviderFilter(event.target.value)}
                    value={eventProviderFilter}
                  >
                    <option value="all">All providers</option>
                    <option value="google">Google Calendar</option>
                    <option value="microsoft">Microsoft Graph</option>
                    <option value="outlook">Outlook</option>
                    <option value="local">Local/manual</option>
                  </select>
                </label>
                <label className="field">
                  <span className="label">Meeting link</span>
                  <select
                    className="input compact-input"
                    onChange={(event) => setEventLinkStatus(event.target.value)}
                    value={eventLinkStatus}
                  >
                    <option value="all">With or without link</option>
                    <option value="has_link">Has meeting link</option>
                    <option value="missing_link">Missing meeting link</option>
                  </select>
                </label>
                <label className="field">
                  <span className="label">Starts after</span>
                  <input
                    className="input compact-input"
                    onChange={(event) => setEventDateFrom(event.target.value)}
                    type="datetime-local"
                    value={eventDateFrom}
                  />
                </label>
                <label className="field">
                  <span className="label">Starts before</span>
                  <input
                    className="input compact-input"
                    onChange={(event) => setEventDateTo(event.target.value)}
                    type="datetime-local"
                    value={eventDateTo}
                  />
                </label>
              </>
            ) : null}
          </form>

          <div className="calendar-automation-panel">
            <div>
              <p className="eyebrow">Automation</p>
              <strong>{bulkCandidateCount} shown event(s) need meetings</strong>
            </div>
            <label className="toggle-field">
              <input
                checked={bulkRequireMeetingLink}
                onChange={(event) => setBulkRequireMeetingLink(event.target.checked)}
                type="checkbox"
              />
              <span>Require meeting link</span>
            </label>
            <button
              className="button primary compact-button"
              disabled={!events.length || !bulkCandidateCount || isBulkCreating}
              onClick={() => void createMeetingsForShownEvents()}
              type="button"
            >
              {isBulkCreating ? "Creating..." : "Create meetings for shown"}
            </button>
          </div>

          <button
            className="button subtle compact-button manual-import-toggle"
            onClick={() => setShowManualImport((current) => !current)}
            type="button"
          >
            {showManualImport ? "Hide manual import" : "Manual import"}
          </button>

          {showManualImport ? (
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
          ) : null}

          {events.length ? (
            <div className="calendar-event-list">
              {events.map((event) => (
                <article className="calendar-event" key={event.id}>
                  <div>
                    <strong>{event.title}</strong>
                    <p className="helper">
                      {formatDate(event.starts_at)}
                      {" / "}
                      {providerLabel(accountById.get(event.calendar_account_id)?.provider || "local")}
                    </p>
                  </div>
                  <div className="meta-row">
                    <span
                      className={`status ${
                        event.imported_meeting_id ? "completed" : "uploaded"
                      }`}
                    >
                      {event.imported_meeting_id ? "Meeting created" : "Needs meeting"}
                    </span>
                    {event.meeting_url ? (
                      <a className="pill link-pill" href={event.meeting_url}>
                        Meeting link
                      </a>
                    ) : null}
                    {event.imported_meeting_id ? (
                      <Link
                        className="pill link-pill"
                        href={`/meetings/${event.imported_meeting_id}`}
                      >
                        Open meeting
                      </Link>
                    ) : (
                      <button
                        className="button subtle compact-button"
                        disabled={creatingMeetingId === event.id}
                        onClick={() => void createMeetingFromEvent(event.id)}
                        type="button"
                      >
                        {creatingMeetingId === event.id
                          ? "Creating..."
                          : "Create meeting"}
                      </button>
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
            <p className="eyebrow">Providers</p>
            <h3>Connections</h3>
          </div>
        </div>
        <div className="provider-status-list">
          {providerStatuses.map((status) => (
            <div className="provider-status" key={status.provider}>
              <div className="related-heading">
                <strong>{status.label}</strong>
                <span className={`status ${status.configured ? "completed" : "uploaded"}`}>
                  {status.configured ? "Configured" : "Missing keys"}
                </span>
              </div>
              <p className="helper">
                {status.configured
                  ? "Ready for OAuth connection."
                  : "Add client ID and secret to enable OAuth."}
              </p>
              {status.client_id_configured ? (
                <a
                  className="button subtle compact-button"
                  href={`${API_BASE_URL}/calendar/oauth/${status.provider}/start?workspace_id=1`}
                >
                  Start OAuth
                </a>
              ) : null}
            </div>
          ))}
        </div>
        <p className="footer-note">
          Connected OAuth calendars sync automatically while this page is open.
        </p>
      </aside>
    </section>
  );
}
