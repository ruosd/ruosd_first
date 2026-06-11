<template>
  <div class="settings">
    <h2>⚙ 系统设置</h2>
    <p>配置记忆系统和向量数据库参数</p>
    <div class="card settings-card">
      <div class="setting-row">
        <div>
          <strong>Ollama 嵌入模型</strong>
          <span>当前: bge-m3:latest</span>
        </div>
        <span class="badge">已配置</span>
      </div>
      <div class="setting-row">
        <div>
          <strong>ChromaDB 模式</strong>
          <span>PersistentClient (内嵌)</span>
        </div>
        <span class="badge">运行中</span>
      </div>
      <div class="setting-row">
        <div>
          <strong>LLM 模型</strong>
          <span>阿里云百炼 deepseek-v4-pro</span>
        </div>
        <span class="badge">已连接</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings { max-width: 640px; margin: 0 auto; }
.settings h2 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
.settings > p { color: var(--text-secondary); font-size: 14px; margin-bottom: 24px; }
.settings-card { padding: 24px; }
.setting-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 0; border-bottom: 1px solid var(--border-light);
}
.setting-row:last-child { border-bottom: none; }
.setting-row strong { display: block; font-size: 14px; color: var(--text); margin-bottom: 2px; }
.setting-row span { font-size: 12px; color: var(--text-muted); }
.badge { font-size: 11px; padding: 4px 10px; border-radius: 20px; background: var(--success-bg); color: var(--success); font-weight: 500; }
</style>
