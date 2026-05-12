import Link from "next/link";
import { api } from "../../lib/api";

type SearchResult = {
  kind: string;
  meeting_id: number;
  meeting_title: string;
  title: string;
  excerpt: string;
  status?: string | null;
};

type Props = {
  searchParams?: {
    q?: string;
  };
};

const kindCopy: Record<string, string> = {
  meeting: "Meeting",
  summary: "AI notes",
  action: "Action item",
};

export default async function SearchPage({ searchParams }: Props) {
  const query = (searchParams?.q || "").trim();
  const results = query
    ? ((await (await api(`/search?q=${encodeURIComponent(query)}`)).json()) as SearchResult[])
    : [];

  return (
    <main className="page">
      <section className="page-header">
        <div>
          <p className="eyebrow">Memory</p>
          <h2>Search</h2>
          <p className="lead">
            Find meetings, transcripts, AI notes, and action items from one place.
          </p>
        </div>
        <div className="actions">
          <Link className="button primary" href="/meetings/new">
            New meeting
          </Link>
        </div>
      </section>

      <section className="panel search-panel">
        <form className="search-form" action="/search">
          <label className="field search-field">
            <span className="label">Search workspace</span>
            <input
              className="input search-input"
              defaultValue={query}
              name="q"
              placeholder="Search decisions, transcripts, owners, risks, or action items"
            />
          </label>
          <button className="button primary" type="submit">
            Search
          </button>
        </form>

        {query ? (
          <div className="section-heading compact search-summary">
            <div>
              <p className="eyebrow">Results</p>
              <h3>{results.length} matches</h3>
            </div>
            <span className="pill">{query}</span>
          </div>
        ) : null}

        {!query ? (
          <div className="empty">
            <div className="empty-inner">
              <h3>Search meeting memory</h3>
              <p className="helper">
                Try a customer name, decision, owner, action, risk, or phrase from
                a transcript.
              </p>
            </div>
          </div>
        ) : results.length === 0 ? (
          <div className="empty">
            <div className="empty-inner">
              <h3>No matches found</h3>
              <p className="helper">
                Search checks meeting titles, transcripts, AI notes, and action
                item text.
              </p>
            </div>
          </div>
        ) : (
          <ul className="search-results">
            {results.map((result, index) => (
              <li className="search-result" key={`${result.kind}-${result.meeting_id}-${index}`}>
                <div className="search-result-header">
                  <div>
                    <span className="status">{kindCopy[result.kind] || result.kind}</span>
                    {result.status ? <span className="pill">{result.status}</span> : null}
                  </div>
                  <Link className="pill link-pill" href={`/meetings/${result.meeting_id}`}>
                    {result.meeting_title}
                  </Link>
                </div>
                <Link className="meeting-title" href={`/meetings/${result.meeting_id}`}>
                  {result.title}
                </Link>
                <p className="helper">{result.excerpt || "Matched this meeting."}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
