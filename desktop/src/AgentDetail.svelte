<script>
  import { onMount, onDestroy } from 'svelte';
  import { t } from './lib/i18n.js';

  export let agent = null;
  export let onback = () => {};

  let details = null;
  let loading = true;
  let error = '';

  const API_BASE = 'http://127.0.0.1:9800';
  let pollTimer;

  onMount(() => {
    fetchDetails();
    pollTimer = setInterval(fetchDetails, 5000);
  });

  onDestroy(() => {
    if (pollTimer) clearInterval(pollTimer);
  });

  async function fetchDetails() {
    if (!agent) return;
    loading = details === null;
    try {
      const res = await fetch(`${API_BASE}/api/agents/${agent.type}/details`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      details = await res.json();
      error = '';
      loading = false;
    } catch (e) {
      loading = false;
      error = e.message;
    }
  }

  function statusDot(activity) {
    if (activity === 'active' || activity === 'busy') return 'yellow';
    if (activity === 'idle') return 'green';
    if (activity === 'not_running') return 'red';
    return 'gray';
  }

  function formatDuration(seconds) {
    if (!seconds && seconds !== 0) return '-';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
  }

  function formatTime(iso) {
    if (!iso) return '-';
    const d = new Date(iso);
    const h = d.getHours().toString().padStart(2,'0');
    const m = d.getMinutes().toString().padStart(2,'0');
    return `${h}:${m}`;
  }

  function formatDate(iso) {
    if (!iso) return '-';
    const d = new Date(iso);
    return `${d.getMonth()+1}/${d.getDate()} ${formatTime(iso)}`;
  }

  $: task = details ? details.current_task : (agent ? agent.current_task : null);
  $: cronJobs = details ? (details.cron_jobs || []) : [];
  $: platforms = details && details.gateway ? (details.gateway.platforms || []) : [];
  $: gwState = details && details.gateway ? details.gateway.state : null;
</script>

<main>
  <header data-tauri-drag-region>
    <button class="back-btn" on:click={onback}>← {$t('back')}</button>
    <span class="dot dot-{statusDot(agent ? agent.activity : 'not_running')}" class:dot-blink={agent && (agent.activity === 'active' || agent.activity === 'busy')}></span>
    <span class="title">{agent ? agent.name : ''}</span>
  </header>

  {#if loading}
    <div class="loading">{$t('loading')}</div>
  {:else if error}
    <div class="error">⚠️ {error}</div>
  {:else}

    <!-- 当前任务 -->
    <div class="section">
      <div class="label">{$t('current_task')}</div>
      {#if task}
        <div class="value">{task.description}</div>
        <div class="row">
          <span>{$t('status')}: <span class="badge running">{$t('running')}</span></span>
          <span>{$t('running_for')}: {formatDuration(task.duration)}</span>
        </div>
      {:else}
        <div class="value dim">{$t('no_current_task')}</div>
      {/if}
    </div>

    <!-- 定时任务 -->
    <div class="section">
      <div class="label">{$t('scheduled_tasks')} ({cronJobs.length})</div>
      {#if cronJobs.length === 0}
        <div class="value dim">{$t('no_scheduled_tasks')}</div>
      {:else}
        {#each cronJobs as job}
          <div class="cron-row">
            <div class="cron-name">
              <span class="cron-dot" class:on={job.enabled}></span>
              {job.name || job.id}
            </div>
            <div class="cron-schedule">{job.schedule}</div>
            {#if job.next_run}
              <div class="cron-next">{formatDate(job.next_run)}</div>
            {/if}
          </div>
        {/each}
      {/if}
    </div>

    <!-- 机器人/接口状态 -->
    <div class="section">
      <div class="label">
        {$t('gateway_status')}
        {#if gwState}
          <span class="gw-badge" class:gw-on={gwState === 'running'} class:gw-off={gwState !== 'running'}>{gwState}</span>
        {/if}
      </div>
      {#if platforms.length === 0}
        <div class="value dim">{$t('no_platforms')}</div>
      {:else}
        {#each platforms as p}
          <div class="platform-row">
            <span class="plat-dot" class:plat-on={p.state === 'connected'} class:plat-off={p.state !== 'connected'}></span>
            <span class="plat-name">{p.name}</span>
            <span class="plat-state" class:plat-ok={p.state === 'connected'} class:plat-err={p.state !== 'connected'}>{p.state}</span>
            {#if p.error}
              <span class="plat-err-msg">{p.error}</span>
            {/if}
          </div>
        {/each}
      {/if}
    </div>

  {/if}
</main>

<style>
  main { background: var(--bg); color: var(--text); font-size: 13px; padding: 10px 12px; min-height: calc(100vh - 36px); }
  header { display: flex; align-items: center; gap: 8px; padding-bottom: 8px; border-bottom: 1px solid var(--border); margin-bottom: 8px; }
  .back-btn { background: none; border: 1px solid var(--border); color: var(--text); padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 12px; }
  .back-btn:hover { background: var(--card-bg); }
  .dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .dot-green { background: var(--green); }
  .dot-yellow { background: var(--yellow); }
  .dot-red { background: var(--red); }
  .dot-gray { background: var(--gray); }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
  .dot-blink { animation: blink 1.2s ease-in-out infinite; }
  .title { font-weight: 600; font-size: 14px; flex: 1; }

  .section { background: var(--card-bg); border-radius: 6px; padding: 10px; margin-bottom: 8px; }
  .label { color: var(--text-dim); font-size: 11px; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }
  .value { font-size: 14px; margin-bottom: 4px; }
  .value.dim { color: var(--text-dim); font-size: 12px; }
  .row { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-dim); margin-top: 4px; }
  .badge { padding: 1px 6px; border-radius: 3px; font-size: 11px; }
  .badge.running { background: rgba(34,197,94,0.15); color: var(--green); }

  .cron-row { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 12px; border-bottom: 1px solid rgba(255,255,255,0.04); }
  .cron-row:last-child { border-bottom: none; }
  .cron-name { flex: 1; display: flex; align-items: center; gap: 6px; }
  .cron-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--gray); flex-shrink: 0; }
  .cron-dot.on { background: var(--green); }
  .cron-schedule { color: var(--yellow); font-family: monospace; font-size: 11px; }
  .cron-next { color: var(--text-dim); font-size: 11px; min-width: 60px; text-align: right; }

  .gw-badge { font-size: 10px; padding: 1px 6px; border-radius: 3px; }
  .gw-on { background: rgba(34,197,94,0.15); color: var(--green); }
  .gw-off { background: rgba(239,68,68,0.15); color: var(--red); }

  .platform-row { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 12px; }
  .plat-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .plat-on { background: var(--green); }
  .plat-off { background: var(--red); }
  .plat-name { flex: 1; font-weight: 500; }
  .plat-state { font-size: 11px; }
  .plat-ok { color: var(--green); }
  .plat-err { color: var(--red); }
  .plat-err-msg { color: var(--text-dim); font-size: 11px; overflow: hidden; text-overflow: ellipsis; max-width: 120px; }

  .loading { text-align: center; padding: 40px 0; color: var(--text-dim); }
  .error { color: var(--red); padding: 20px 0; text-align: center; }
</style>
