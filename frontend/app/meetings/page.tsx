import Link from 'next/link';
import { api } from '../../lib/api';

export default async function MeetingsPage(){
  const meetings = await (await api('/meetings')).json();
  return <main><h2>Meetings</h2><Link href='/meetings/new'>New Meeting</Link><ul>{meetings.map((m:any)=><li key={m.id}><Link href={`/meetings/${m.id}`}>{m.title}</Link> - {m.status}</li>)}</ul></main>
}
