'use client';
import { useEffect, useState } from 'react';

export default function MeetingDetail({params}:{params:{id:string}}){
 const [meeting,setMeeting]=useState<any>(null); const [output,setOutput]=useState<any>(null);
 async function refresh(){ const base='http://localhost:8000/api'; setMeeting(await fetch(`${base}/meetings/${params.id}`).then(r=>r.json())); try{setOutput(await fetch(`${base}/meetings/${params.id}/ai-output`).then(r=>r.json()));}catch{}
 }
 async function process(){await fetch(`http://localhost:8000/api/meetings/${params.id}/process`,{method:'POST'}); await refresh();}
 useEffect(()=>{refresh();},[]);
 if(!meeting) return <div>Loading...</div>;
 return <main><h2>{meeting.title}</h2><p>Status: {meeting.status}</p><button onClick={process}>Process</button><a href={`http://localhost:8000/api/meetings/${params.id}/export/markdown`}>Export Markdown</a><h3>Transcript</h3><pre>{meeting.transcript_text}</pre><h3>AI Notes</h3><pre>{JSON.stringify(output?.summary_json,null,2)}</pre><h3>Action Items</h3><ul>{output?.summary_json?.action_items?.map((a:any,i:number)=><li key={i}>{a.task} ({a.priority})</li>)}</ul></main>
}
