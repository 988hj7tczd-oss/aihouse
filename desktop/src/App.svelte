<script>
  import { onMount, onDestroy } from 'svelte';
  import AgentDetail from './AgentDetail.svelte';

  const API_BASE = 'http://127.0.0.1:9800';

  let invoke;
  try {
    // Static import cannot be used in catch, so we try once eagerly
    import('@tauri-apps/api/core').then(m => invoke = m.invoke).catch(() => {});
  } catch {}

  let agents = [];
  let loading = true;
  let error = '';
  let selected = null;

  let poll, retry;

  onMount(() => { load(); poll = setInterval(load, 3000); });
  onDestroy(() => { clearInterval(poll); if (retry) clearInterval(retry); });

  async function api(path) {
    if (invoke) {
      try {
        const r = await invoke('fetch_api', { path });
        return typeof r === 'string' ? JSON.parse(r) : r;
      } catch (_) {}
    }
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  }

  async function load() {
    loading = agents.length === 0;
    try {
      const d = await api('/api/status');
      agents = d.agents || [];
      error = ''; loading = false;
      if (retry) { clearInterval(retry); retry = null; }
      if (!selected && agents.length) selected = agents[0].type;
    } catch (e) {
      loading = false; error = e.message;
      if (!retry) retry = setInterval(load, 10000);
    }
  }

  function dot(a) {
    if (a === 'active' || a === 'busy') return 'y';
    if (a === 'idle') return 'g';
    if (a === 'not_running') return 'r';
    return 'x';
  }

  function label(a) {
    const m = { active: '运行中', idle: '空闲', busy: '忙碌', error: '异常', stuck: '卡住', not_running: '未运行' };
    return m[a] || a;
  }

  $: sel = agents.find(a => a.type === selected) || agents[0] || null;
  $: ac = agents.filter(a => a.activity === 'active' || a.activity === 'busy').length;
  $: ic = agents.filter(a => a.activity === 'idle').length;
  $: oc = agents.filter(a => a.activity === 'not_running').length;
</script>

<div class="app">
  <aside>
    <div class="head">
      <div class="title">AIHouse</div>
      <div class="ver">v0.1.0</div>
    </div>

    <div class="list">
      {#if loading && !agents.length}
        <div class="empty">加载中...</div>
      {:else if !agents.length}
        <div class="empty">{error || '无 Agent'}</div>
      {:else}
        {#each agents as a}
          <div class="item" class:on={selected === a.type} on:click={() => selected = a.type}>
            <span class="pt pt-{dot(a.activity)}" class:blink={a.activity === 'active' || a.activity === 'busy'}></span>
            <div class="info">
              <div class="nm">{a.name}</div>
              <div class="st">{label(a.activity)}</div>
            </div>
            {#if a.current_task}
              <div class="pre">{a.current_task.description.slice(0, 16)}</div>
            {/if}
          </div>
        {/each}
      {/if}
    </div>

    <div class="foot">
      <span class="c-green">● {ac}</span>
      <span class="c-dim">● {ic}</span>
      <span class="c-red">● {oc}</span>
    </div>
  </aside>

  <main>
    {#if error}
      <div class="err">⚠️ {error} <button on:click={load}>重试</button></div>
    {/if}
    {#if sel}
      <AgentDetail agent={sel} api={api} />
    {:else if !loading}
      <div class="empty-detail">选择左侧 Agent 查看详情</div>
    {/if}
  </main>
</div>

<style>
  .app { display:flex; height:100vh; }
  aside { width:260px; display:flex; flex-direction:column; border-right:1px solid var(--border); padding:12px; gap:8px; }
  main { flex:1; padding:16px 20px; overflow-y:auto; }
  .head { display:flex; align-items:baseline; gap:8px; padding:0 4px 8px; border-bottom:1px solid var(--border); }
  .title { font-size:18px; font-weight:700; }
  .ver { font-size:11px; color:var(--muted); }
  .list { flex:1; display:flex; flex-direction:column; gap:4px; overflow-y:auto; }
  .item { display:flex; align-items:center; gap:8px; padding:8px 10px; border-radius:6px; cursor:pointer; transition:background 0.1s; }
  .item:hover { background:var(--hover); }
  .item.on { background:var(--selected); }
  .pt { width:10px; height:10px; border-radius:50%; flex-shrink:0; }
  .pt-g { background:var(--green); } .pt-y { background:var(--yellow); } .pt-r { background:var(--red); } .pt-x { background:var(--muted); }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.15} }
  .blink { animation:blink 1.2s ease-in-out infinite; }
  .info { flex:1; min-width:0; }
  .nm { font-size:14px; font-weight:600; } .st { font-size:11px; color:var(--dim); }
  .pre { font-size:11px; color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:80px; }
  .foot { display:flex; gap:14px; font-size:12px; padding:8px 4px 0; border-top:1px solid var(--border); }
  .c-green { color:var(--green); } .c-dim { color:var(--dim); } .c-red { color:var(--red); }
  .empty { padding:30px; text-align:center; color:var(--muted); font-size:13px; }
  .err { background:rgba(248,81,73,0.1); border:1px solid rgba(248,81,73,0.25); border-radius:8px; padding:8px 12px; display:flex; justify-content:space-between; align-items:center; font-size:13px; margin-bottom:10px; }
  .err button { background:var(--card); border:1px solid var(--border); color:var(--text); border-radius:4px; padding:2px 10px; cursor:pointer; font-size:12px; }
  .empty-detail { padding:60px; text-align:center; color:var(--muted); font-size:14px; }
</style>
