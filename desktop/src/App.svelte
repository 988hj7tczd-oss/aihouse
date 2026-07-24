<script>
  import { onMount, onDestroy } from 'svelte';
  import { t } from './lib/i18n.js';
  import TaskDetail from './TaskDetail.svelte';
  import History from './History.svelte';
  import Settings from './Settings.svelte';

  let agents = [];
  let summary = {};
  let tasksToday = {};
  let notifications = [];
  let error = '';
  let loading = true;
  let activeTab = 'dashboard';
  let selectedAgent = null;

  const API_BASE = 'http://127.0.0.1:9800';

  let pollTimer;
  let retryTimer;

  onMount(() => {
    fetchAll();
    pollTimer = setInterval(fetchAll, 3000);
  });

  onDestroy(() => {
    if (pollTimer) clearInterval(pollTimer);
    if (retryTimer) clearInterval(retryTimer);
  });

  async function fetchAll() {
    await Promise.all([fetchStatus(), fetchTasksToday(), fetchNotifications()]);
  }

  async function fetchStatus() {
    loading = agents.length === 0;
    try {
      const res = await fetch(`${API_BASE}/api/status`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      agents = data.agents || [];
      summary = data.summary || {};
      error = '';
      loading = false;
      if (retryTimer) { clearInterval(retryTimer); retryTimer = null; }
    } catch (e) {
      loading = false;
      error = `${$t('connection_failed')}: ${e.message}`;
      if (!retryTimer) retryTimer = setInterval(fetchStatus, 10000);
    }
  }

  async function fetchTasksToday() {
    try {
      const res = await fetch(`${API_BASE}/api/tasks/today`);
      if (!res.ok) return;
      tasksToday = await res.json();
    } catch (e) { /* silent */ }
  }

  async function fetchNotifications() {
    try {
      const res = await fetch(`${API_BASE}/api/tasks?limit=5`);
      if (!res.ok) return;
      const data = await res.json();
      notifications = (data.tasks || []).filter(t => t.status === 'failed' || t.status === 'stuck').slice(0, 5);
    } catch (e) { /* silent */ }
  }

  async function refresh() {
    try {
      await fetch(`${API_BASE}/api/control/refresh`);
      fetchAll();
    } catch (e) { error = `刷新失败: ${e.message}`; }
  }

  function selectAgent(agent) {
    selectedAgent = agent;
    activeTab = 'detail';
  }

  function goBack() { activeTab = 'dashboard'; }

  function activityColor(activity) {
    const map = { active: 'var(--green)', idle: 'var(--blue)', busy: 'var(--yellow)', error: 'var(--red)', stuck: 'var(--red)', not_running: 'var(--gray)' };
    return map[activity] || 'var(--gray)';
  }

  function activityLabel(activity) {
    const names = ['running_label', 'idle_label', 'busy_label', 'error_label', 'stuck_label', 'not_running_label'];
    const keys = ['active', 'idle', 'busy', 'error', 'stuck', 'not_running'];
    const idx = keys.indexOf(activity);
    return idx >= 0 ? $t(names[idx]) : activity;
  }

  function formatDuration(seconds) {
    if (!seconds && seconds !== 0) return '-';
    if (seconds < 60) return `${Math.round(seconds)}${$t('seconds_unit')}`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}${$t('minutes')}`;
    return `${(seconds / 3600).toFixed(1)}h`;
  }

  function formatTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
  }

  function summaryColor(color) {
    if (color === 'green') return $t('all_normal');
    if (color === 'blue') return $t('all_idle');
    if (color === 'yellow') return $t('agent_stuck');
    if (color === 'red') return $t('agent_error');
    return $t('agent_unknown');
  }

  function overallStatus() {
    if (summary.color === 'red') return $t('error_label');
    if (summary.color === 'yellow') return $t('stuck_label');
    if (summary.color === 'blue') return $t('idle_label');
    return $t('all_normal');
  }

  function overallColor() {
    return summary.color === 'red' ? 'var(--red)' :
           summary.color === 'yellow' ? 'var(--yellow)' :
           summary.color === 'blue' ? 'var(--blue)' : 'var(--green)';
  }
</script>

<main>
  {#if activeTab === 'dashboard'}
    <!-- 状态概览栏 -->
    <div class="status-bar" style="--status-color: {overallColor()}">
      <span class="status-dot" style="background: {overallColor()}"></span>
      <span class="status-text">{summaryColor(summary.color)}</span>
      <span class="status-right" style="flex:1; text-align:right; color:var(--text-dim); font-size:12px;">
        Agent {$t('agent')} {summary.total || 0} · 3s
      </span>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card"><span class="stat-num">{tasksToday.total || 0}</span><span class="stat-label">{$t('total_tasks')}</span></div>
      <div class="stat-card"><span class="stat-num" style="color:var(--green)">{tasksToday.completed || 0}</span><span class="stat-label">{$t('completed')}</span></div>
      <div class="stat-card"><span class="stat-num" style="color:var(--red)">{(tasksToday.failed||0)+(tasksToday.stuck||0)}</span><span class="stat-label">{$t('failed_stuck')}</span></div>
      <div class="stat-card"><span class="stat-num" style="color:var(--yellow)">${(tasksToday.total_cost || 0).toFixed(2)}</span><span class="stat-label">{$t('todays_cost')}</span></div>
    </div>

    <!-- 错误横幅 -->
    {#if error}
      <div class="error-banner"><span>⚠️ {error}</span><button on:click={fetchStatus}>{$t('retry')}</button></div>
    {/if}

    <!-- Agent 状态列表 -->
    <div class="agent-section">
      <div class="section-header">
        <span>{$t('agent_status')}</span>
        <button class="refresh-btn" on:click={refresh}>{$t('refresh')}</button>
      </div>
      <div class="agent-list">
        {#if loading && agents.length === 0}
          <div class="loading">{$t('loading')}</div>
        {:else if agents.length === 0}
          <div class="empty-message">{$t('no_agent_data')}</div>
        {:else}
          {#each agents as agent}
            <div class="agent-card" on:click={() => selectAgent(agent)}>
              <div class="card-top">
                <span class="dot" style="background: {activityColor(agent.activity)}"></span>
                <span class="agent-name">{agent.name}</span>
                <span class="agent-status">{activityLabel(agent.activity)}</span>
                {#if agent.current_task}
                  <span class="task-desc">{agent.current_task.description}</span>
                  <span class="task-time">{formatDuration(agent.current_task.duration)}</span>
                {/if}
                {#if agent.current_task?.estimated_cost}
                  <span class="task-cost">${agent.current_task.estimated_cost.toFixed(2)}</span>
                {/if}
              </div>
              {#if agent.current_task?.files_changed && agent.current_task.files_changed.length > 0}
                <div class="card-files">
                  {#each agent.current_task.files_changed.slice(0, 3) as f}
                    <span class="file-tag">{f}</span>
                  {/each}
                </div>
              {/if}
              {#if agent.activity === 'stuck' || agent.activity === 'error'}
                <div class="card-warn">⚠️ {agent.current_task?.error_message || $t('stuck_label')}</div>
              {/if}
            </div>
          {/each}
        {/if}
      </div>
    </div>

    <!-- 通知区域 -->
    {#if notifications.length > 0}
      <div class="notif-section">
        <div class="section-header"><span>{$t('recent_notifications')}</span></div>
        {#each notifications as n}
          <div class="notif-row" class:warn={n.status === 'stuck'} class:err={n.status === 'failed'}>
            <span>{n.status === 'stuck' ? '⚠️' : '❌'} {formatTime(n.started_at)}</span>
            <span>{n.agent_name}: {n.description}</span>
          </div>
        {/each}
      </div>
    {/if}

  {:else if activeTab === 'detail'}
    <TaskDetail agent={selectedAgent} onback={goBack} />
  {:else if activeTab === 'history'}
    <History onback={goBack} />
  {:else if activeTab === 'settings'}
    <Settings onback={goBack} />
  {/if}
</main>

<nav class="tab-bar" data-tauri-drag-region>
  <button class="tab" class:active={activeTab === 'dashboard'} on:click={() => activeTab = 'dashboard'}>{$t('dashboard')}</button>
  <button class="tab" class:active={activeTab === 'history'} on:click={() => activeTab = 'history'}>{$t('history')}</button>
  <button class="tab" class:active={activeTab === 'settings'} on:click={() => activeTab = 'settings'}>{$t('settings')}</button>
</nav>

<style>
  :global(*) { margin:0; padding:0; box-sizing:border-box; }
  :root {
    --bg: #1a1a2e; --card-bg: #16213e; --text: #e0e0e0;
    --text-dim: #808080; --green: #22c55e; --blue: #3b82f6;
    --yellow: #eab308; --red: #ef4444; --gray: #6b7280; --border: #2a2a4a;
  }

  main { min-height: calc(100vh - 36px); background: var(--bg); color: var(--text); font-size: 13px; padding: 12px 16px; display: flex; flex-direction: column; gap: 10px; }

  .tab-bar { display: flex; background: var(--card-bg); border-top: 1px solid var(--border); height: 36px; align-items: center; padding: 0 8px; gap: 4px; }
  .tab { background: none; border: none; color: var(--text-dim); padding: 6px 14px; font-size: 12px; cursor: pointer; border-radius: 4px; }
  .tab.active { color: var(--text); background: var(--bg); }
  .tab:hover { color: var(--text); }

  .status-bar { display: flex; align-items: center; gap: 8px; background: var(--card-bg); border-radius: 8px; padding: 10px 14px; border-left: 3px solid var(--status-color, var(--green)); }
  .status-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .status-text { font-weight: 600; font-size: 14px; }

  .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .stat-card { background: var(--card-bg); border-radius: 8px; padding: 12px; text-align: center; }
  .stat-num { display: block; font-size: 22px; font-weight: 700; }
  .stat-label { display: block; font-size: 11px; color: var(--text-dim); margin-top: 2px; }

  .section-header { display: flex; justify-content: space-between; align-items: center; font-weight: 600; font-size: 13px; margin-bottom: 6px; }
  .refresh-btn { background: none; border: 1px solid var(--border); color: var(--text-dim); padding: 3px 10px; border-radius: 4px; cursor: pointer; font-size: 11px; }
  .refresh-btn:hover { color: var(--text); border-color: var(--text-dim); }

  .agent-section { flex: 1; }
  .agent-list { display: flex; flex-direction: column; gap: 6px; }
  .agent-card { background: var(--card-bg); border-radius: 8px; padding: 10px 12px; cursor: pointer; transition: background 0.15s; }
  .agent-card:hover { background: color-mix(in srgb, var(--card-bg) 90%, var(--text)); }
  .card-top { display: flex; align-items: center; gap: 8px; }
  .dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .agent-name { font-weight: 600; min-width: 90px; }
  .agent-status { font-size: 12px; min-width: 44px; color: var(--text-dim); }
  .task-desc { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 12px; }
  .task-time { font-size: 12px; color: var(--text-dim); min-width: 44px; text-align: right; }
  .task-cost { font-size: 12px; color: var(--yellow); min-width: 50px; text-align: right; }
  .card-files { display: flex; gap: 4px; margin-top: 6px; flex-wrap: wrap; }
  .file-tag { font-size: 11px; background: var(--bg); color: var(--text-dim); padding: 2px 6px; border-radius: 3px; }
  .card-warn { font-size: 11px; color: var(--red); margin-top: 4px; }

  .notif-section { border-top: 1px solid var(--border); padding-top: 8px; }
  .notif-row { display: flex; gap: 8px; font-size: 12px; padding: 4px 8px; border-radius: 4px; margin-top: 4px; }
  .notif-row.warn { background: rgba(234,179,8,0.1); }
  .notif-row.err { background: rgba(239,68,68,0.1); }

  .error-banner { background: rgba(239,68,68,0.15); border: 1px solid var(--red); border-radius: 6px; padding: 8px 12px; display: flex; justify-content: space-between; align-items: center; font-size: 12px; }
  .error-banner button { background: var(--red); color: white; border: none; border-radius: 3px; padding: 2px 8px; cursor: pointer; font-size: 12px; }

  .loading { text-align: center; padding: 40px 0; color: var(--text-dim); }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loading::before { content: ''; display: block; width: 24px; height: 24px; border: 2px solid var(--border); border-top-color: var(--blue); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 8px; }
  .empty-message { color: var(--text-dim); text-align: center; padding: 20px 0; }
</style>
