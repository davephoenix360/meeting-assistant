import { api } from "../../lib/api";
import {
  CalendarClient,
  type CalendarAccount,
  type CalendarEvent,
  type CalendarProviderStatus,
} from "./CalendarClient";

export default async function CalendarPage() {
  const [accounts, events, providers] = await Promise.all([
    (await api("/calendar/accounts?workspace_id=1&include_disconnected=true")).json() as Promise<CalendarAccount[]>,
    (await api("/calendar/events?workspace_id=1")).json() as Promise<CalendarEvent[]>,
    (await api("/calendar/providers")).json() as Promise<CalendarProviderStatus[]>,
  ]);

  return (
    <main className="page">
      <section className="page-header">
        <div>
          <p className="eyebrow">Integrations</p>
          <h2>Calendar</h2>
          <p className="lead">
            Prepare calendar accounts and imported events before provider sync is connected.
          </p>
        </div>
      </section>

      <CalendarClient
        initialAccounts={accounts}
        initialEvents={events}
        providerStatuses={providers}
      />
    </main>
  );
}
