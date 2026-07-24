<script>
  import { onMount, onDestroy } from 'svelte';
  import { t } from './lib/i18n.js';
  import AgentDetail from './AgentDetail.svelte';
  import History from './History.svelte';
  import Settings from './Settings.svelte';

  let agents = [];
  let summary = {};
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
    await fetchStatus();
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

  function selectAgent(agent) {
    selectedAgent = agent;
    activeTab = 'detail';
  }

  function goBack() { activeTab = 'dashboard'; }

  function statusDot(activity) {
    if (activity === 'active' || activity === 'busy') return 'yellow';
    if (activity === 'idle') return 'green';
    if (activity === 'not_running') return 'red';
    return 'gray';
  }

  function statusLabel(activity) {
    const map = { active: $t('running_label'), idle: $t('idle_label'), busy: $t('busy_label'), error: $t('error_label'), stuck: $t('stuck_label'), not_running: $t('not_running_label') };
    return map[activity] || activity;
  }

  function formatTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
  }

  function overallColor() {
    const c = summary.color;
    return c === 'red' ? 'var(--red)' : c === 'yellow' ? 'var(--yellow)' : c === 'blue' ? 'var(--blue)' : 'var(--green)';
  }
</script>

<main>
  {#if activeTab === 'dashboard'}
    <!-- 状态栏 -->
    <div class="status-bar" style="border-left-color: {overallColor()}">
      <span class="status-title">AIHouse</span>
      <span class="status-count">{agents.length} {$t('agent')}</span>
    </div>

    <!-- 错误条 -->
    {#if error}
      <div class="error-banner"><span>⚠️ {error}</span><button on:click={fetchStatus}>{$t('retry')}</button></div>
    {/if}

    <!-- Agent 卡片列表 -->
    <div class="agent-list">
      {#if loading && agents.length === 0}
        <div class="loading">{$t('loading')}</div>
      {:else if agents.length === 0}
        <div class="empty-message">{$t('no_agent_data')}</div>
      {:else}
        {#each agents as agent}
          <div class="agent-card" on:click={() => selectAgent(agent)}>
            <div class="dot-row">
              <span class="dot dot-{statusDot(agent.activity)}" class:dot-blink={agent.activity === 'active' || agent.activity === 'busy'}></span>
              <span class="agent-name">{agent.name}</span>
              <span class="agent-status">{statusLabel(agent.activity)}</span>
            </div>
            {#if agent.current_task}
              <div class="task-row">{agent.current_task.description}</div>
            {/if}
          </div>
        {/each}
      {/if}
    </div>

  {:else if activeTab === 'detail'}
    <AgentDetail agent={selectedAgent} onback={goBack} />
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
  * { margin:0; padding:0; box-sizing:border-box; }

  main { min-height: calc(100vh - 36px); background: var(--bg); color: var(--text); font-size: 13px; padding: 10px 12px; display: flex; flex-direction: column; gap: 8px; }

  .tab-bar { display: flex; background: var(--card-bg); border-top: 1px solid var(--border); height: 36px; align-items: center; padding: 0 8px; gap: 4px; }
  .tab { background: none; border: none; color: var(--text-dim); padding: 6px 14px; font-size: 12px; cursor: pointer; border-radius: 4px; }
  .tab.active { color: var(--text); background: var(--bg); }
  .tab:hover { color: var(--text); }

  .status-bar { display: flex; align-items: center; gap: 8px; background: var(--card-bg); border-radius: 8px; padding: 8px 12px; border-left: 3px solid var(--green); }
  .status-title { font-weight: 700; font-size: 14px; }
  .status-count { font-size: 12px; color: var(--text-dim); }

  .error-banner { background: rgba(239,68,68,0.15); border: 1px solid var(--red); border-radius: 6px; padding: 6px 10px; display: flex; justify-content: space-between; align-items: center; font-size: 12px; }
  .error-banner button { background: var(--red); color: white; border: none; border-radius: 3px; padding: 2px 8px; cursor: pointer; font-size: 11px; }

  .agent-list { display: flex; flex-direction: column; gap: 6px; flex: 1; overflow-y: auto; }
  .agent-card { background: var(--card-bg); border-radius: 8px; padding: 10px 12px; cursor: pointer; transition: background 0.15s; }
  .agent-card:hover { background: color-mix(in srgb, var(--card-bg) 90%, var(--text)); }

  .dot-row { display: flex; align-items: center; gap: 8px; }
  .dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .dot-green { background: var(--green); }
  .dot-yellow { background: var(--yellow); }
  .dot-red { background: var(--red); }
  .dot-gray { background: var(--gray); }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }
  .dot-blink { animation: blink 1.2s ease-in-out infinite; }

  .agent-name { font-weight: 600; font-size: 14px; flex: 1; }
  .agent-status { font-size: 12px; color: var(--text-dim); }

  .task-row { font-size: 12px; color: var(--text-dim); margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-left: 18px; }

  .loading { text-align: center; padding: 40px 0; color: var(--text-dim); }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loading::before { content: ''; display: block; width: 24px; height: 24px; border: 2px solid var(--border); border-top-color: var(--blue); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 8px; }
  .empty-message { color: var(--text-dim); text-align: center; padding: 20px 0; }
</style>
