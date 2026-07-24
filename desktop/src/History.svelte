<script>
  import { onMount, onDestroy } from 'svelte';
  import { t } from './lib/i18n.js';

  export let onback = () => {};

  let tasks = [];
  let loading = true;
  let error = '';
  let filterStatus = '';
  let filterAgent = '';

  const API_BASE = 'http://127.0.0.1:9800';
  let pollTimer;

  onMount(() => {
    fetchTasks();
    pollTimer = setInterval(fetchTasks, 5000);
  });

  onDestroy(() => { if (pollTimer) clearInterval(pollTimer); });

  async function fetchTasks() {
    loading = true;
    try {
      let url = `${API_BASE}/api/tasks?limit=50`;
      if (filterAgent) url += `&agent=${encodeURIComponent(filterAgent)}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      tasks = data.tasks || [];
      if (filterStatus) {
        tasks = tasks.filter(t => t.status === filterStatus);
      }
      error = '';
    } catch (e) {
      error = `${$t('load_failed')}: ${e.message}`;
    }
    loading = false;
  }

  function formatTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    const month = (d.getMonth()+1).toString().padStart(2,'0');
    const day = d.getDate().toString().padStart(2,'0');
    const h = d.getHours().toString().padStart(2,'0');
    const m = d.getMinutes().toString().padStart(2,'0');
    return `${month}-${day} ${h}:${m}`;
  }

  function statusClass(s) {
    if (s === 'completed') return 'done';
    if (s === 'failed') return 'fail';
    if (s === 'stuck') return 'stuck';
    if (s === 'running') return 'run';
    return '';
  }
</script>

<header data-tauri-drag-region>
  <button class="back-btn" on:click={onback}>{$t('back')}</button>
  <span class="title">{$t('history_records')}</span>
</header>

<main>
  <div class="filter-row">
    <select class="filter-sel" bind:value={filterStatus} on:change={fetchTasks}>
      <option value="">{$t('all_status')}</option>
      <option value="completed">{$t('completed')}</option>
      <option value="failed">{$t('failed')}</option>
      <option value="stuck">{$t('stuck')}</option>
      <option value="running">{$t('running')}</option>
    </select>
    <button class="back-btn" on:click={fetchTasks}>{$t('refresh')}</button>
  </div>

  <div class="task-list">
    {#if loading}
      <div class="empty">{$t('loading')}</div>
    {:else if error}
      <div class="empty" style="color:var(--red)">{error}</div>
    {:else if tasks.length === 0}
      <div class="empty">{$t('no_task_records')}</div>
    {:else}
      <div class="task-header">
        <span class="th time">{$t('time')}</span>
        <span class="th agent">{$t('agent')}</span>
        <span class="th status">{$t('status')}</span>
        <span class="th duration">{$t('duration')}</span>
        <span class="th desc">{$t('description')}</span>
      </div>
      {#each tasks as task}
        <div class="task-row">
          <span class="td time">{formatTime(task.started_at)}</span>
          <span class="td agent">{task.agent_name}</span>
          <span class="td status"><span class="tag {statusClass(task.status)}">{task.status}</span></span>
          <span class="td duration">{task.duration ? `${Math.round(task.duration)}s` : '-'}</span>
          <span class="td desc">{task.description}</span>
        </div>
      {/each}
    {/if}
  </div>
</main>

<style>
  header { display: flex; align-items: center; gap: 8px; padding: 10px 16px; background: var(--card-bg); border-bottom: 1px solid var(--border); }
  .back-btn { background: none; border: 1px solid var(--border); color: var(--text); padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; }
  .back-btn:hover { background: var(--bg); }
  .title { font-weight: 600; font-size: 14px; flex: 1; }
  main { min-height: calc(100vh - 44px); background: var(--bg); color: var(--text); font-size: 13px; padding: 12px 16px; display: flex; flex-direction: column; gap: 8px; }
  .filter-row { display: flex; align-items: center; gap: 8px; padding-bottom: 8px; border-bottom: 1px solid var(--border); justify-content: flex-end; }
  .filter-sel { background: var(--card-bg); color: var(--text); border: 1px solid var(--border); border-radius: 4px; padding: 4px 8px; font-size: 12px; }
  .task-list { flex: 1; overflow-y: auto; }
  .task-header { display: flex; gap: 8px; padding: 6px 8px; font-size: 11px; color: var(--text-dim); border-bottom: 1px solid var(--border); }
  .task-row { display: flex; gap: 8px; padding: 7px 8px; font-size: 12px; border-bottom: 1px solid color-mix(in srgb, var(--border) 50%, transparent); }
  .task-row:hover { background: var(--card-bg); }
  .th { font-weight: 500; }
  .td { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .time { min-width: 90px; }
  .agent { min-width: 80px; }
  .status { min-width: 60px; }
  .duration { min-width: 50px; text-align: right; }
  .desc { flex: 1; }
  .tag { padding: 1px 6px; border-radius: 3px; font-size: 11px; }
  .tag.done { background: rgba(34,197,94,0.15); color: var(--green); }
  .tag.fail { background: rgba(239,68,68,0.15); color: var(--red); }
  .tag.stuck { background: rgba(234,179,8,0.15); color: var(--yellow); }
  .tag.run { background: rgba(59,130,246,0.15); color: var(--blue); }
  .empty { text-align: center; padding: 40px 0; color: var(--text-dim); }
</style>
