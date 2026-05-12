import Link from "next/link";
import { api } from "../../lib/api";
import { ActionItemsClient, type ActionItem } from "./ActionItemsClient";

export default async function ActionItemsPage() {
  const items = (await (await api("/action-items")).json()) as ActionItem[];

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

      <ActionItemsClient initialItems={items} />
    </main>
  );
}
