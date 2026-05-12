import Link from "next/link";
import { api } from "../../lib/api";
import {
  ActionItemsClient,
  type ActionItem,
  type MeetingOption,
} from "./ActionItemsClient";

export default async function ActionItemsPage() {
  const [items, meetings] = await Promise.all([
    (await api("/action-items?include_archived=true")).json() as Promise<ActionItem[]>,
    (await api("/meetings")).json() as Promise<MeetingOption[]>,
  ]);

  return (
    <main className="page">
      <section className="page-header">
        <div>
          <p className="eyebrow">Workspace</p>
          <h2>Action items</h2>
          <p className="lead">
            Track follow-up work across every processed meeting and jump back to
            the source context when needed.
          </p>
        </div>
        <div className="actions">
          <Link className="button primary" href="/meetings/new">
            New meeting
          </Link>
        </div>
      </section>

      <ActionItemsClient initialItems={items} meetings={meetings} />
    </main>
  );
}
