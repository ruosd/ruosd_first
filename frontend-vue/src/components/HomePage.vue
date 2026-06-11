<template>
  <div class="home">
    <div class="home-card">
      <div class="brand">电商客服助手</div>
      <p class="subtitle">智能 · 高效 · 全天候</p>
      <div class="actions">
        <button @click="$router.push('/login')" class="btn btn-primary btn-lg">用户登录</button>
        <button @click="$router.push('/admin/login')" class="btn btn-secondary btn-lg">管理员登录</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(160deg, #f8fafc 0%, #eff6ff 50%, #f1f5f9 100%);
  padding: 24px;
}
.home-card {
  text-align: center; max-width: 400px; width: 100%;
  animation: fadeInUp 0.6s ease;
}
.brand {
  font-size: 32px; font-weight: 700; color: var(--text);
  letter-spacing: -0.5px; margin-bottom: 8px;
}
.subtitle {
  font-size: 16px; color: var(--text-secondary); margin-bottom: 40px;
  letter-spacing: 2px;
}
.actions { display: flex; flex-direction: column; gap: 12px; }
</style>
