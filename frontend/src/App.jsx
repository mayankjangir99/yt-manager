import React, { useEffect, useState } from 'react'
import {
  Youtube, LayoutDashboard, Video, CalendarClock, Settings as SettingsIcon,
  ChartNoAxesCombined, Upload, FolderOpen, RefreshCw, CheckCircle2, AlertCircle,
  Clock3, Trash2, Save, Link2, ExternalLink, FileVideo, Play, X, ShieldCheck,
  Tags, CalendarDays
} from 'lucide-react'
import { api, errText } from './api'

const initialSettings = {
  folder_path: '', folder_default_type: 'long', watch_folder_enabled: false, auto_metadata: true,
  auto_schedule: true, auto_publish: false, shorts_per_week: 5,
  long_videos_per_week: 2, shorts_time: '18:00', long_videos_time: '12:00',
  publish_days: [0,1,2,3,4,5,6], timezone: 'Asia/Kolkata',
  default_visibility: 'private'
}
const dayNames = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
const prettyDate = v => v ? new Date(v).toLocaleString() : 'Not scheduled'

function App() {
  const [page, setPage] = useState('Overview')
  const [videos, setVideos] = useState([])
  const [settings, setSettings] = useState(initialSettings)
  const [channel, setChannel] = useState({connected:false, channel:null})
  const [logs, setLogs] = useState([])
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [editing, setEditing] = useState(null)
  const [uploadType, setUploadType] = useState('short')
  const [file, setFile] = useState(null)
  const [scheduleTime, setScheduleTime] = useState('')
  const [search, setSearch] = useState('')

  async function refresh() {
    try {
      const [v,s,c,l] = await Promise.all([
        api.get('/videos'), api.get('/settings'), api.get('/youtube/status'), api.get('/logs?limit=20')
      ])
      setVideos(v.data); setSettings(s.data); setChannel(c.data); setLogs(l.data)
    } catch(e) { setNotice(`Backend connection error: ${errText(e)}. Is FastAPI running?`) }
  }
  useEffect(() => { refresh() }, [])
  async function run(action, success) {
    setBusy(true); setNotice('')
    try { await action(); await refresh(); setNotice(success || 'Saved successfully.') }
    catch(e) { setNotice(errText(e)) }
    finally { setBusy(false) }
  }
  const updateSetting = (key, value) => setSettings(s => ({...s, [key]:value}))
  async function saveSettings() {
    await run(() => api.put('/settings', settings), 'Settings saved.')
  }
  async function upload() {
    if (!file) return setNotice('Choose a video file first.')
    const form = new FormData(); form.append('file', file); form.append('video_type', uploadType)
    await run(() => api.post('/videos/upload', form), 'Video added to your library.')
    setFile(null)
    const input = document.getElementById('video-file'); if (input) input.value = ''
  }
  async function connectYoutube() {
    await run(async () => {
      const {data} = await api.get('/youtube/oauth/start')
      window.location.href = data.authorization_url
    })
  }
  async function saveVideo() {
    await run(() => api.patch(`/videos/${editing.id}`, {
      title: editing.title, description: editing.description,
      tags: editing.tagsText.split(',').map(x=>x.trim()).filter(Boolean),
      video_type: editing.video_type, category_id: editing.category_id
    }), 'Video details saved.')
    setEditing(null)
  }
  async function autoSchedule(id) {
    await run(() => api.post(`/videos/${id}/auto-schedule`), 'Video scheduled.')
  }
  async function scheduleSpecific(id) {
    if (!scheduleTime) return setNotice('Choose a date and time first.')
    await run(() => api.post(`/videos/${id}/schedule`, {scheduled_at:new Date(scheduleTime).toISOString()}), 'Schedule saved.')
    setScheduleTime('')
  }
  const filtered = videos.filter(v => `${v.filename} ${v.title} ${v.status}`.toLowerCase().includes(search.toLowerCase()))
  const queued = videos.filter(v => ['draft','queued','scheduled','failed'].includes(v.status)).length
  const published = videos.filter(v => v.youtube_video_id).length

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-icon"><Youtube size={23}/></div><div><b>Creator Studio AI</b><small>YouTube Manager</small></div></div>
      <div className="nav-label">WORKSPACE</div>
      {[
        ['Overview',LayoutDashboard],['Video Library',Video],['Scheduler',CalendarClock],
        ['Analytics',ChartNoAxesCombined],['Settings',SettingsIcon]
      ].map(([name,Icon])=><button key={name} className={`nav-item ${page===name?'active':''}`} onClick={()=>setPage(name)}><Icon size={18}/>{name}</button>)}
      <div className="sidebar-bottom">
        <div className={`connection ${channel.connected?'connected':''}`}><span className="status-dot"/><div><b>{channel.connected ? (channel.channel?.title || 'YouTube connected') : 'YouTube not connected'}</b><small>{channel.connected?'Account authorized':'Connect in Settings'}</small></div></div>
        <small className="muted">Local-first · FastAPI backend</small>
      </div>
    </aside>
    <main className="main">
      <header className="topbar"><div><div className="eyebrow">CHANNEL WORKSPACE</div><h1>{page}</h1></div><div className="top-actions"><button className="btn secondary" onClick={refresh}><RefreshCw size={16}/> Refresh</button><button className="avatar">CS</button></div></header>
      {notice && <div className="notice"><AlertCircle size={17}/><span>{notice}</span><button onClick={()=>setNotice('')}><X size={15}/></button></div>}
      {page==='Overview' && <section className="page-content">
        <div className="welcome"><div><div className="eyebrow light">YOUR CREATOR WORKSPACE</div><h2>Manage your channel, visually.</h2><p>Upload, organize, and schedule Shorts and long-form videos without typing commands.</p></div><div className="welcome-mark"><Youtube size={52}/></div></div>
        <div className="stats-grid">
          <Stat icon={<FileVideo/>} label="Total videos" value={videos.length} tone="purple"/>
          <Stat icon={<Clock3/>} label="In queue" value={queued} tone="blue"/>
          <Stat icon={<CheckCircle2/>} label="Uploaded to YouTube" value={published} tone="green"/>
          <Stat icon={<CalendarDays/>} label="Auto publishing" value={settings.auto_publish?'On':'Off'} tone="orange"/>
        </div>
        <div className="two-col">
          <div className="panel"><div className="panel-head"><div><h3>Quick upload</h3><p>Add a video to your library</p></div><Upload size={19}/></div>
            <label className="dropzone" htmlFor="video-file"><Upload size={25}/><b>{file ? file.name : 'Choose a video file'}</b><span>MP4, MOV, MKV, AVI, WEBM · local upload</span><input id="video-file" type="file" accept="video/*,.mkv,.avi,.webm" onChange={e=>setFile(e.target.files?.[0]||null)}/></label>
            <div className="form-row"><label>Video format<select value={uploadType} onChange={e=>setUploadType(e.target.value)}><option value="short">Shorts</option><option value="long">Long video</option></select></label><button className="btn primary" disabled={busy || !file} onClick={upload}><Upload size={16}/> Add to library</button></div>
          </div>
          <div className="panel"><div className="panel-head"><div><h3>Automation status</h3><p>Current saved rules</p></div><SettingsIcon size={19}/></div>
            <ToggleRow label="Watch local folder" detail={settings.folder_path || 'No folder selected'} value={settings.watch_folder_enabled} onChange={v=>updateSetting('watch_folder_enabled',v)} compact/>
            <ToggleRow label="Generate starter metadata" detail="Create a basic title and description" value={settings.auto_metadata} onChange={v=>updateSetting('auto_metadata',v)} compact/>
            <ToggleRow label="Auto schedule" detail="Assign publishing slots to new videos" value={settings.auto_schedule} onChange={v=>updateSetting('auto_schedule',v)} compact/>
            <ToggleRow label="Auto publish" detail="Upload and schedule on YouTube" value={settings.auto_publish} onChange={v=>updateSetting('auto_publish',v)} compact/>
            <button className="btn secondary full" onClick={()=>run(()=>api.put('/settings',settings),'Automation settings saved.')}>Save automation toggles</button>
          </div>
        </div>
        <VideoTable videos={videos.slice(0,5)} onEdit={v=>setEditing({...v,tagsText:(v.tags||[]).join(', ')})} onSchedule={autoSchedule} onUpload={id=>run(()=>api.post(`/videos/${id}/upload-now`),'Uploaded privately to YouTube.')} />
      </section>}
      {page==='Video Library' && <section className="page-content"><div className="panel"><div className="panel-head"><div><h3>Video library</h3><p>Edit metadata, schedule, or upload privately.</p></div><div className="search"><input placeholder="Search videos..." value={search} onChange={e=>setSearch(e.target.value)}/></div></div><VideoTable videos={filtered} onEdit={v=>setEditing({...v,tagsText:(v.tags||[]).join(', ')})} onSchedule={autoSchedule} onUpload={id=>run(()=>api.post(`/videos/${id}/upload-now`),'Uploaded privately to YouTube.')} onDelete={id=>run(()=>api.delete(`/videos/${id}`),'Video removed from library.')}/></div></section>}
      {page==='Scheduler' && <section className="page-content"><div className="panel"><div className="panel-head"><div><h3>Publishing queue</h3><p>Configure recurring rules in Settings or schedule individual videos below.</p></div><CalendarClock size={20}/></div><div className="schedule-summary"><div><span>Shorts / week</span><b>{settings.shorts_per_week}</b><small>at {settings.shorts_time} IST</small></div><div><span>Long videos / week</span><b>{settings.long_videos_per_week}</b><small>at {settings.long_videos_time} IST</small></div><div><span>Publishing days</span><b>{(settings.publish_days||[]).length}/7</b><small>{dayNames.filter((d,i)=>(settings.publish_days||[]).includes(i)).join(', ') || 'None'}</small></div></div><VideoTable videos={videos.filter(v=>['draft','queued','scheduled','failed','scheduled_on_youtube'].includes(v.status))} onEdit={v=>setEditing({...v,tagsText:(v.tags||[]).join(', ')})} onSchedule={autoSchedule} onUpload={id=>run(()=>api.post(`/videos/${id}/upload-now`),'Uploaded privately to YouTube.')}/></div></section>}
      {page==='Analytics' && <section className="page-content"><div className="panel"><div className="panel-head"><div><h3>Channel analytics</h3><p>Connect your channel to retrieve available channel statistics.</p></div><ChartNoAxesCombined size={20}/></div>{channel.connected && channel.channel ? <div className="stats-grid"><Stat label="Subscribers" value={channel.channel.subscriber_count ?? 'Hidden'} tone="purple"/><Stat label="Channel views" value={Number(channel.channel.view_count||0).toLocaleString()} tone="blue"/><Stat label="Videos" value={channel.channel.video_count ?? '—'} tone="green"/></div> : <div className="empty"><ChartNoAxesCombined size={34}/><b>Connect YouTube first</b><span>Channel statistics will appear here when authorized.</span><button className="btn primary" onClick={connectYoutube}><Link2 size={16}/> Connect YouTube</button></div>}<p className="muted">This starter shows channel-level statistics. Date-range reports and video-level analytics can be added using the YouTube Analytics API.</p></div><div className="panel"><h3>Recent activity</h3><Logs logs={logs}/></div></section>}
      {page==='Settings' && <section className="page-content">
        <div className="panel"><div className="panel-head"><div><h3>YouTube connection</h3><p>Authorize this app to upload videos to your channel.</p></div><ShieldCheck size={20}/></div><div className="connect-row"><div className={`youtube-big ${channel.connected?'ok':''}`}><Youtube size={27}/></div><div className="grow"><b>{channel.connected ? (channel.channel?.title || 'YouTube connected') : 'Connect your YouTube channel'}</b><p>{channel.connected?'Your channel is authorized.':'Google OAuth is required before upload and analytics calls.'}</p></div><button className="btn primary" onClick={connectYoutube}><ExternalLink size={16}/>{channel.connected?'Reconnect':'Connect YouTube'}</button></div></div>
        <div className="panel"><div className="panel-head"><div><h3>Folder automation</h3><p>Use a path on the computer running the FastAPI backend.</p></div><FolderOpen size={20}/></div><label className="field-label">Watched folder path</label><input className="text-input" placeholder="Example: C:\\Users\\YourName\\Videos\\ToUpload" value={settings.folder_path||''} onChange={e=>updateSetting('folder_path',e.target.value)}/><div className="helper">The folder watcher imports supported video files. It does not delete or move originals.</div><label className="field-label">Default type for new folder videos</label><select value={settings.folder_default_type||'long'} onChange={e=>updateSetting('folder_default_type',e.target.value)}><option value="short">Shorts</option><option value="long">Long video</option></select><div className="helper">Files with “short” in their filename are automatically classified as Shorts; otherwise this default is used.</div><ToggleRow label="Enable folder watcher" detail="Watch for new video files" value={settings.watch_folder_enabled} onChange={v=>updateSetting('watch_folder_enabled',v)}/><ToggleRow label="Generate starter metadata" detail="Fill a basic description and tags for new videos" value={settings.auto_metadata} onChange={v=>updateSetting('auto_metadata',v)}/><ToggleRow label="Auto schedule new videos" detail="Use the rules below when a video is discovered" value={settings.auto_schedule} onChange={v=>updateSetting('auto_schedule',v)}/><ToggleRow label="Automatic upload and YouTube scheduling" detail="Uploads eligible videos and sets YouTube publish time. Off by default." value={settings.auto_publish} onChange={v=>updateSetting('auto_publish',v)}/></div>
        <div className="panel"><div className="panel-head"><div><h3>Publishing rules</h3><p>Times use the selected timezone. Weekly values are maximum target counts.</p></div><CalendarClock size={20}/></div><div className="settings-grid"><label>Shorts per week<input type="number" min="0" max="28" value={settings.shorts_per_week} onChange={e=>updateSetting('shorts_per_week',Number(e.target.value))}/></label><label>Long videos per week<input type="number" min="0" max="14" value={settings.long_videos_per_week} onChange={e=>updateSetting('long_videos_per_week',Number(e.target.value))}/></label><label>Shorts time<input type="time" value={settings.shorts_time} onChange={e=>updateSetting('shorts_time',e.target.value)}/></label><label>Long video time<input type="time" value={settings.long_videos_time} onChange={e=>updateSetting('long_videos_time',e.target.value)}/></label><label>Timezone<select value={settings.timezone} onChange={e=>updateSetting('timezone',e.target.value)}><option>Asia/Kolkata</option><option>UTC</option><option>America/New_York</option><option>Europe/London</option></select></label><label>Default visibility<select value={settings.default_visibility} onChange={e=>updateSetting('default_visibility',e.target.value)}><option value="private">Private (recommended)</option><option value="unlisted">Unlisted</option><option value="public">Public</option></select></label></div><div className="days"><span>Allowed publishing days</span>{dayNames.map((d,i)=><label key={d} className={`day ${settings.publish_days?.includes(i)?'selected':''}`}><input type="checkbox" checked={settings.publish_days?.includes(i)||false} onChange={e=>updateSetting('publish_days',e.target.checked?[...(settings.publish_days||[]),i].sort():settings.publish_days.filter(x=>x!==i))}/>{d}</label>)}</div><button className="btn primary" disabled={busy} onClick={saveSettings}><Save size={16}/> Save all settings</button></div>
        <div className="panel"><div className="panel-head"><div><h3>Activity log</h3><p>Recent upload and scheduler events.</p></div><RefreshCw size={18}/></div><Logs logs={logs}/></div>
      </section>}
    </main>
    {editing && <div className="modal-backdrop" onClick={()=>setEditing(null)}><div className="modal" onClick={e=>e.stopPropagation()}><div className="modal-head"><div><h2>Edit video</h2><p>{editing.filename}</p></div><button className="icon-btn" onClick={()=>setEditing(null)}><X size={18}/></button></div><label>Title (max 100 characters)<input maxLength="100" value={editing.title||''} onChange={e=>setEditing({...editing,title:e.target.value})}/></label><label>Description<textarea rows="5" value={editing.description||''} onChange={e=>setEditing({...editing,description:e.target.value})}/></label><label>Tags (comma separated)<input value={editing.tagsText} onChange={e=>setEditing({...editing,tagsText:e.target.value})}/></label><div className="settings-grid"><label>Video type<select value={editing.video_type} onChange={e=>setEditing({...editing,video_type:e.target.value})}><option value="short">Shorts</option><option value="long">Long video</option></select></label><label>Category ID<input value={editing.category_id||'22'} onChange={e=>setEditing({...editing,category_id:e.target.value})}/></label></div><div className="modal-actions"><button className="btn secondary" onClick={()=>setEditing(null)}>Cancel</button><button className="btn primary" onClick={saveVideo}><Save size={16}/> Save changes</button></div></div></div>}
  </div>
}
function Stat({icon,label,value,tone}) { return <div className="stat-card"><div className={`stat-icon ${tone}`}>{icon}</div><div><span>{label}</span><strong>{value}</strong></div></div> }
function ToggleRow({label,detail,value,onChange,compact=false}) { return <div className={`toggle-row ${compact?'compact':''}`}><div className="grow"><b>{label}</b><small>{detail}</small></div><button className={`switch ${value?'on':''}`} aria-pressed={value} onClick={()=>onChange(!value)}><span/></button></div> }
function VideoTable({videos,onEdit,onSchedule,onUpload,onDelete}) {
  if(!videos.length) return <div className="empty"><Video size={32}/><b>No videos yet</b><span>Upload a video or enable folder watching in Settings.</span></div>
  return <div className="table-wrap"><table><thead><tr><th>VIDEO</th><th>TYPE</th><th>STATUS</th><th>SCHEDULE</th><th>ACTIONS</th></tr></thead><tbody>{videos.map(v=><tr key={v.id}><td><div className="video-name"><div className="file-icon"><Play size={15}/></div><div><b>{v.title||v.filename}</b><small>{v.filename}</small></div></div></td><td><span className="pill">{v.video_type==='short'?'Shorts':'Long'}</span></td><td><span className={`status-pill ${v.status==='failed'?'error':v.youtube_video_id?'success':''}`}>{v.status.replaceAll('_',' ')}</span>{v.last_error && <small className="error-text">{v.last_error}</small>}</td><td>{prettyDate(v.scheduled_at)}</td><td><div className="row-actions"><button title="Edit metadata" onClick={()=>onEdit(v)} className="icon-btn"><SettingsIcon size={16}/></button>{!v.youtube_video_id && <button title="Auto schedule" onClick={()=>onSchedule(v.id)} className="icon-btn"><CalendarClock size={16}/></button>}{!v.youtube_video_id && <button title="Upload privately now" onClick={()=>onUpload(v.id)} className="icon-btn"><Upload size={16}/></button>}{onDelete && !v.youtube_video_id && <button title="Delete library item" onClick={()=>onDelete(v.id)} className="icon-btn danger"><Trash2 size={16}/></button>}</div></td></tr>)}</tbody></table></div>
}
function Logs({logs}) { return logs.length ? <div className="logs">{logs.slice(0,12).map(l=><div className="log-row" key={l.id}><span className={`log-dot ${l.level==='error'?'red':''}`}/><div><b>{l.message}</b><small>{new Date(l.created_at).toLocaleString()}</small></div></div>)}</div> : <div className="empty compact-empty"><span>No activity recorded yet.</span></div> }
export default App
