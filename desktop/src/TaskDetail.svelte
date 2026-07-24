<script>
  import { t } from './lib/i18n.js';

  export let agent = null;
  export let onback = () => {};

  function activityLabel(activity) {
    const names = ['running_label','idle_label','busy_label','error_label','stuck_label','not_running_label'];
    const keys = ['active','idle','busy','error','stuck','not_running'];
    const idx = keys.indexOf(activity);
    return idx >= 0 ? $t(names[idx]) : activity;
  }

  function activityColor(activity) {
    const map = { active:'var(--green)', idle:'var(--blue)', busy:'var(--yellow)', error:'var(--red)', stuck:'var(--red)', not_running:'var(--gray)' };
    return map[activity] || 'var(--gray)';
  }

  function formatDuration(seconds) {
    if (!seconds && seconds !== 0) return '-';
    if (seconds < 60) return `${Math.round(seconds)}${$t('seconds_unit')}`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}${$t('minutes')}`;
    return `${(seconds / 3600).toFixed(1)}h`;
  }

  function formatTime(iso) {
    if (!iso) return '-';
    const d = new Date(iso);
    return `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
  }

  $: task = agent ? agent.current_task : null;
  $: last = agent ? agent.last_task : null;
</script>

<main>
  <header data-tauri-drag-region>
    <button class="back-btn" on:click={onback}>{$t('back')}</button>
    <span class="title">{agent ? agent.name : ''}</span>
    {#if agent}
      <span class="dot" style="background: {activityColor(agent.activity)}"></span>
    {/if}
  </header>

  {#if task}
    <div class="section">
      <div class="label">{$t('current_task')}</div>
      <div class="value">{task.description}</div>
      <div class="row">
        <span>{$t('status')}: <span class="badge" class:running={task.status === 'running'}>{task.status}</span></span>
        <span>{$t('running_for')}: {formatDuration(task.duration)}</span>
      </div>
      <div class="row">
        <span>{$t('started')}: {formatTime(task.started_at)}</span>
        {#if task.estimated_cost}
          <span>{$t('cost')}: ${task.estimated_cost.toFixed(2)}</span>
        {/if}
      </div>
    </div>
  {:else}
    <div class="section">
      <div class="label">{$t('no_current_task')}</div>
    </div>
  {/if}

  {#if agent}
    <div class="section">
      <div class="label">{$t('status')}</div>
      <div class="value">{activityLabel(agent.activity)}</div>
      <div class="row"><span>{$t('pid')}: {agent.pid || '-'}</span></div>
      <div class="row"><span>{$t('todays_tasks')}: {agent.tasks_today || 0}</span></div>
    </div>
  {/if}
</main>

<style>
  main { width: 380px; background: var(--bg); color: var(--text); font-size: 13px; padding: 12px; }
  header { display: flex; align-items: center; gap: 8px; padding-bottom: 10px; border-bottom: 1px solid var(--border); margin-bottom: 10px; }
  .back-btn { background: none; border: 1px solid var(--border); color: var(--text); padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 12px; }
  .back-btn:hover { background: var(--card-bg); }
  .title { font-weight: 600; font-size: 14px; flex: 1; }
  .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .section { background: var(--card-bg); border-radius: 6px; padding: 10px; margin-bottom: 8px; }
  .label { color: var(--text-dim); font-size: 11px; margin-bottom: 4px; }
  .value { font-size: 14px; margin-bottom: 6px; }
  .row { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-dim); margin-top: 4px; }
  .badge { padding: 1px 6px; border-radius: 3px; font-size: 11px; }
  .badge.running { background: rgba(34,197,94,0.15); color: var(--green); }
</style>
