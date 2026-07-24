<script>
  import { onMount } from 'svelte';
  import { t, locale } from './lib/i18n.js';

  export let onback = () => {};

  let version = '';
  let configData = { agents: [], notifications: [] };
  let status = '';

  const API_BASE = 'http://127.0.0.1:9800';

  // ── 主题 ──
  let theme = 'dark';
  if (typeof localStorage !== 'undefined') {
    theme = localStorage.getItem('aihouse_theme') || 'dark';
  }
  function setTheme(v) {
    theme = v;
    localStorage.setItem('aihouse_theme', v);
    applyTheme(v);
  }
  function applyTheme(t) {
    if (typeof document === 'undefined') return;
    const root = document.documentElement;
    if (t === 'light') {
      root.style.setProperty('--bg', '#f5f5f7');
      root.style.setProperty('--card-bg', '#ffffff');
      root.style.setProperty('--text', '#1d1d1f');
      root.style.setProperty('--text-dim', '#86868b');
      root.style.setProperty('--border', '#d2d2d7');
    } else if (t === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      applyTheme(prefersDark ? 'dark' : 'light');
    } else {
      root.style.setProperty('--bg', '#1a1a2e');
      root.style.setProperty('--card-bg', '#16213e');
      root.style.setProperty('--text', '#e0e0e0');
      root.style.setProperty('--text-dim', '#808080');
      root.style.setProperty('--border', '#2a2a4a');
    }
  }

  // ── 窗口置顶 ──
  let alwaysOnTop = true;
  if (typeof localStorage !== 'undefined') {
    alwaysOnTop = localStorage.getItem('aihouse_ontop') !== 'false';
  }
  function toggleAlwaysOnTop() {
    localStorage.setItem('aihouse_ontop', String(alwaysOnTop));
    try {
      const w = window.__TAURI__?.window;
      if (w?.getCurrentWindow) {
        w.getCurrentWindow().setAlwaysOnTop(alwaysOnTop);
      }
    } catch (e) { /* silent */ }
  }

  // ── 轮询间隔 ──
  let pollInterval = 10;
  if (typeof localStorage !== 'undefined') {
    pollInterval = parseInt(localStorage.getItem('aihouse_poll') || '10', 10);
  }
  function setPollInterval() {
    const v = Math.max(5, Math.min(300, pollInterval || 10));
    pollInterval = v;
    localStorage.setItem('aihouse_poll', String(v));
  }

  onMount(async () => {
    applyTheme(theme);
    try {
      const h = await fetch(`${API_BASE}/api/health`);
      if (h.ok) { const d = await h.json(); version = d.version || ''; }
    } catch (e) { status = 'backend_disconnected'; }
    try {
      const c = await fetch(`${API_BASE}/api/config`);
      if (c.ok) configData = await c.json();
    } catch (e) { /* silent */ }
  });
</script>

<main>
  <header data-tauri-drag-region>
    <button class="back-btn" on:click={onback}>{$t('back')}</button>
    <span class="title">{$t('settings')}</span>
  </header>

  <div class="scroll-area">
    <!-- 语言 -->
    <div class="section">
      <div class="label">{$t('language')}</div>
      <select class="sel" value={$locale} on:change={(e) => locale.set(e.target.value)}>
        <option value="zh">{$t('chinese')}</option>
        <option value="en">{$t('english')}</option>
      </select>
    </div>

    <!-- 主题 -->
    <div class="section">
      <div class="label">{$t('theme')}</div>
      <div class="theme-options">
        <button class="theme-btn" class:active={theme === 'dark'} on:click={() => setTheme('dark')}>{$t('dark')}</button>
        <button class="theme-btn" class:active={theme === 'light'} on:click={() => setTheme('light')}>{$t('light')}</button>
        <button class="theme-btn" class:active={theme === 'system'} on:click={() => setTheme('system')}>{$t('system')}</button>
      </div>
    </div>

    <!-- 窗口置顶 -->
    <div class="section">
      <div class="label">{$t('window_on_top')}</div>
      <label class="switch">
        <input type="checkbox" bind:checked={alwaysOnTop} on:change={toggleAlwaysOnTop}>
        <span class="slider"></span>
      </label>
      <span class="hint">{alwaysOnTop ? $t('on_top') : $t('not_on_top')}</span>
    </div>

    <!-- 轮询间隔 -->
    <div class="section">
      <div class="label">{$t('poll_interval')}</div>
      <div class="row">
        <input class="inp" type="number" min="5" max="300" bind:value={pollInterval} on:change={setPollInterval} />
        <span class="hint">5-300 {$t('seconds')}</span>
      </div>
    </div>

    <!-- 通知配置 -->
    <div class="section">
      <div class="label">{$t('notifications')}</div>
      {#if configData.notifications && configData.notifications.length > 0}
        {#each configData.notifications as n}
          <div class="notif-row">
            <span>{n.type}</span>
            <span class="hint">{(n.events || []).join(', ')}</span>
          </div>
        {/each}
      {:else}
        <div class="hint">{$t('no_notifications')}</div>
      {/if}
    </div>

    <!-- 已启用 Agent -->
    <div class="section">
      <div class="label">{$t('monitored_agents')}</div>
      {#if configData.agents && configData.agents.length > 0}
        {#each configData.agents as a}
          <div class="agent-item">
            <span>{a.name}</span>
            <span class="badge" class:on={a.enabled !== false} class:off={a.enabled === false}>
              {a.enabled !== false ? $t('enabled') : $t('disabled')}
            </span>
          </div>
        {/each}
      {:else}
        <div class="hint">{$t('no_config')}</div>
      {/if}
    </div>

    <!-- 版本信息 -->
    <div class="section">
      <div class="label">{$t('version')}</div>
      <div class="value">AIHouse v{version || '?'}</div>
    </div>

    <!-- 打开配置文件 -->
    <div class="section">
      <button class="cfg-btn" on:click={() => window.open('file:///Users/Zhuanz/.aihouse/config.yaml', '_blank')}>
        {$t('open_config')}
      </button>
    </div>
  </div>
</main>

<style>
  main { width: 380px; background: var(--bg); color: var(--text); font-size: 13px; padding: 12px; max-height: 450px; display: flex; flex-direction: column; }
  header { display: flex; align-items: center; gap: 8px; padding-bottom: 10px; border-bottom: 1px solid var(--border); margin-bottom: 10px; flex-shrink: 0; }
  .back-btn { background: none; border: 1px solid var(--border); color: var(--text); padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 12px; }
  .back-btn:hover { background: var(--card-bg); }
  .title { font-weight: 600; font-size: 14px; flex: 1; }
  .scroll-area { overflow-y: auto; flex: 1; }
  .section { background: var(--card-bg); border-radius: 6px; padding: 10px; margin-bottom: 8px; }
  .label { color: var(--text-dim); font-size: 11px; margin-bottom: 4px; }
  .value { font-size: 13px; }
  .hint { color: var(--text-dim); font-size: 11px; margin-left: 8px; }
  .row { display: flex; align-items: center; }
  .sel { background: var(--bg); color: var(--text); border: 1px solid var(--border); border-radius: 4px; padding: 4px 8px; font-size: 12px; width: 100%; }
  .inp { background: var(--bg); color: var(--text); border: 1px solid var(--border); border-radius: 4px; padding: 4px 8px; font-size: 12px; width: 80px; }
  .theme-options { display: flex; gap: 8px; }
  .theme-btn { padding: 6px 12px; border: 1px solid var(--border); border-radius: 4px; background: var(--card-bg); color: var(--text); cursor: pointer; font-size: 12px; }
  .theme-btn.active { border-color: var(--blue); background: rgba(59,130,246,0.15); }
  .notif-row { display: flex; justify-content: space-between; font-size: 12px; padding: 3px 0; }
  .agent-item { display: flex; justify-content: space-between; font-size: 12px; padding: 3px 0; }
  .badge { font-size: 11px; padding: 1px 6px; border-radius: 3px; }
  .badge.on { background: rgba(34,197,94,0.15); color: var(--green); }
  .badge.off { background: rgba(239,68,68,0.15); color: var(--red); }
  .switch { position: relative; display: inline-block; width: 36px; height: 20px; vertical-align: middle; }
  .switch input { opacity: 0; width: 0; height: 0; }
  .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background: var(--border); border-radius: 20px; transition: 0.3s; }
  .slider:before { position: absolute; content: ''; height: 14px; width: 14px; left: 3px; bottom: 3px; background: white; border-radius: 50%; transition: 0.3s; }
  .switch input:checked + .slider { background: var(--blue); }
  .switch input:checked + .slider:before { transform: translateX(16px); }
  .cfg-btn { width: 100%; padding: 8px; border: 1px solid var(--blue); border-radius: 4px; background: rgba(59,130,246,0.1); color: var(--blue); cursor: pointer; font-size: 12px; text-align: center; }
  .cfg-btn:hover { background: rgba(59,130,246,0.2); }
</style>
