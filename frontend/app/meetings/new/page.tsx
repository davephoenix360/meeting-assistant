'use client';
import { useState } from 'react';

export default function NewMeeting(){
 const [title,setTitle]=useState(''); const [workspaceId,setWorkspaceId]=useState('1'); const [transcript,setTranscript]=useState('');
 async function submit(){
  const base='http://localhost:8000/api';
  const m=await fetch(`${base}/meetings`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,workspace_id:Number(workspaceId),source_type:'transcript'})}).then(r=>r.json());
  await fetch(`${base}/meetings/${m.id}/transcript`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({transcript_text:transcript})});
  window.location.href=`/meetings/${m.id}`;
 }
 return <main><h2>Create Meeting</h2><input placeholder='Title' value={title} onChange={e=>setTitle(e.target.value)}/><textarea value={transcript} onChange={e=>setTranscript(e.target.value)} /><button onClick={submit}>Create</button></main>
}
