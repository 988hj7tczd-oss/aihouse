<script>
  import { onMount, onDestroy } from 'svelte';

  export let agent = null;
  export let api = null;

  let d = null, notifs = [], loading = true, err = '', poll;

  onMount(() => { fetch(); poll = setInterval(fetch, 5000); });
  onDestroy(() => { if (poll) clearInterval(poll); });

  async function fetch() { await Promise.all([det(), ntf()]); }

  async function det() {
    if (!agent) return;
    try {
      const r = await api(`/api/status/${agent.type}`);
      d = r; err = ''; loading = false;
    } catch (e) { loading = false; err = e.message; }
  }

  async function ntf() {
    try {
      const r = await api('/api/tasks?limit=5');
      notifs = (r.tasks || []).filter(t => t.status === 'failed' || t.status === 'stuck').slice(0, 5);
    } catch {}
  }

  function dot(a) {
    if (a === 'active' || a === 'busy') return 'y';
    if (a === 'idle') return 'g'; if (a === 'not_running') return 'r'; return 'x';
  }

  function dur(s) {
    if (!s && s !== 0) return '-';
    if (s < 60) return `${Math.round(s)}s`;
    if (s < 3600) return `${Math.round(s/60)}m ${Math.round(s%60)}s`;
    return `${(s/3600).toFixed(1)}h`;
  }

  function tm(iso) {
    if (!iso) return '-';
    const z = new Date(iso);
    return `${String(z.getHours()).padStart(2,'0')}:${String(z.getMinutes()).padStart(2,'0')}`;
  }

  function dt(iso) {
    if (!iso) return '-';
    const z = new Date(iso);
    return `${z.getMonth()+1}/${z.getDate()} ${tm(iso)}`;
  }

  $: act = agent ? agent.activity : 'not_running';
  $: tk = d ? d.current_task : (agent ? agent.current_task : null);
  $: jobs = d ? (d.cron_jobs || []) : [];
  $: plats = d && d.gateway ? (d.gateway.platforms || []) : [];
  $: gw = d && d.gateway ? d.gateway.state : null;
</script>

<div class="p">
  <div class="bar">
    <span class="pt pt-{dot(act)}" class:blink={act === 'active' || act === 'busy'}></span>
    <span class="nm">{agent ? agent.name : ''}</span>
    <span class="pid">PID {agent ? agent.pid || '-' : '-'}</span>
  </div>

  {#if loading}
    <div class="cx" style="text-align:center;padding:40px 0;color:var(--muted);font-size:13px;">加载中...</div>
  {:else}

    <div class="cx">
      <div class="h">当前任务</div>
      {#if tk}
        <div class="desc">{tk.description}</div>
        <div class="g2">
          <div><span>状态</span><b style="color:var(--green)">运行中</b></div>
          <div><span>已运行</span><b>{dur(tk.duration)}</b></div>
          {#if tk.model_name}<div><span>模型</span><b>{tk.model_name}</b></div>{/if}
          {#if tk.estimated_cost}<div><span>费用</span><b style="color:var(--yellow)">${tk.estimated_cost.toFixed(4)}</b></div>{/if}
          {#if tk.estimated_tokens}<div><span>Token</span><b>{tk.estimated_tokens.toLocaleString()}</b></div>{/if}
        </div>
      {:else}
        <div class="dim">当前无运行任务</div>
      {/if}
    </div>

    <div class="cx">
      <div class="h">
        机器人/接口
        {#if gw}
          <span class="tag" class:on={gw === 'running'} class:off={gw !== 'running'}>{gw}</span>
        {/if}
      </div>
      {#if !plats.length}
        <div class="dim">暂无机器人连接</div>
      {:else}
        {#each plats as p}
          <div class="rw">
            <span class="dot-md" class:on={p.state === 'connected'}></span>
            <span class="rn">{p.name}</span>
            <span class="stt" class:ok={p.state === 'connected'}>{p.state}</span>
            {#if p.error}<span class="er">{p.error}</span>{/if}
          </div>
        {/each}
      {/if}
    </div>

    <div class="cx">
      <div class="h">定时任务 {jobs.length ? `(${jobs.length})` : ''}</div>
      {#if !jobs.length}
        <div class="dim">暂无定时任务</div>
      {:else}
        {#each jobs as j}
          <div class="rw">
            <span class="dot-sm" class:on={j.enabled}></span>
            <span class="rn">{j.name || j.id}</span>
            <span class="cd">{j.schedule}</span>
            {#if j.next_run}<span class="dt">{dt(j.next_run)}</span>{/if}
          </div>
        {/each}
      {/if}
    </div>

    <div class="cx">
      <div class="h">告警 {notifs.length ? `(${notifs.length})` : ''}</div>
      {#if !notifs.length}
        <div class="dim">暂无告警</div>
      {:else}
        {#each notifs as n}
          <div class="rw al" class:stuck={n.status === 'stuck'} class:fail={n.status === 'failed'}>
            <span class="ico">{n.status === 'stuck' ? '⚠' : '✕'}</span>
            <span class="rn">{n.agent_name}: {n.description}</span>
            <span class="dt">{tm(n.started_at)}</span>
          </div>
        {/each}
      {/if}
    </div>

  {/if}
</div>

<style>
  .p { display:flex; flex-direction:column; gap:10px; max-width:600px; }
  .bar { display:flex; align-items:center; gap:10px; padding-bottom:10px; border-bottom:1px solid var(--border); }
  .pt { width:12px; height:12px; border-radius:50%; flex-shrink:0; }
  .pt-g { background:var(--green); } .pt-y { background:var(--yellow); } .pt-r { background:var(--red); } .pt-x { background:var(--muted); }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.15} }
  .blink { animation:blink 1.2s ease-in-out infinite; }
  .nm { font-size:18px; font-weight:700; flex:1; }
  .pid { font-size:12px; color:var(--dim); font-family:monospace; }
  .cx { background:var(--card); border:1px solid var(--border); border-radius:8px; padding:12px 14px; }
  .h { font-size:12px; font-weight:600; color:var(--dim); margin-bottom:8px; display:flex; align-items:center; gap:6px; text-transform:uppercase; letter-spacing:0.5px; }
  .desc { font-size:15px; line-height:1.4; margin-bottom:8px; }
  .g2 { display:grid; grid-template-columns:1fr 1fr; gap:4px 16px; }
  .g2 > div { display:flex; justify-content:space-between; font-size:13px; }
  .g2 span { color:var(--dim); } .g2 b { font-weight:500; }
  .dim { color:var(--muted); font-size:12px; padding:4px 0; }
  .rw { display:flex; align-items:center; gap:8px; padding:5px 0; font-size:13px; border-bottom:1px solid rgba(255,255,255,0.04); }
  .rw:last-child { border-bottom:none; }
  .rn { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .cd { color:var(--yellow); font-family:monospace; font-size:12px; }
  .dt { color:var(--muted); font-size:12px; white-space:nowrap; }
  .dot-sm { width:6px; height:6px; border-radius:50%; background:var(--border); flex-shrink:0; }
  .dot-sm.on { background:var(--green); }
  .tag { font-size:10px; padding:1px 6px; border-radius:3px; }
  .tag.on { background:rgba(52,208,88,0.12); color:var(--green); }
  .tag.off { background:rgba(248,81,73,0.12); color:var(--red); }
  .dot-md { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
  .dot-md.on { background:var(--green); } .dot-md.off { background:var(--red); }
  .stt { font-size:12px; } .stt.ok { color:var(--green); }
  .er { color:var(--red); font-size:12px; margin-left:auto; }
  .rw.al { padding:5px 8px; border-radius:6px; margin-top:2px; border-bottom:none; }
  .rw.stuck { background:rgba(255,204,0,0.06); }
  .rw.fail { background:rgba(248,81,73,0.06); }
  .ico { flex-shrink:0; }
</style>
