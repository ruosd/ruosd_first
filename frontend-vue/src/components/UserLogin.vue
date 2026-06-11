<template>
  <div class="login-page">
    <div class="login-card card">
      <button @click="$router.push('/')" class="back-link">← 返回</button>
      <h1>用户登录</h1>
      <form @submit.prevent="handleLogin">
        <input v-model="usernameOrEmail" class="input" type="text" placeholder="用户名或邮箱" required :disabled="loading" />
        <input v-model="password" class="input" type="password" placeholder="密码" required :disabled="loading" />
        <p v-if="error" class="err">{{ error }}</p>
        <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
      <p class="footer">还没有账号？<router-link to="/register">立即注册</router-link></p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'; import { useRouter } from 'vue-router'; import { userAPI } from '../api/user.js'
const router = useRouter(); const usernameOrEmail = ref(''); const password = ref(''); const loading = ref(false); const error = ref('')
const handleLogin = async () => {
  if (!usernameOrEmail.value || !password.value) { error.value = '请输入用户名和密码'; return }
  loading.value = true; error.value = ''
  try { await userAPI.login(usernameOrEmail.value, password.value); router.push('/chat') }
  catch (e) { error.value = e.message || '登录失败' }
  finally { loading.value = false }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(160deg, #f8fafc 0%, #eff6ff 50%, #f1f5f9 100%); padding: 24px;
}
.login-card { width: 100%; max-width: 400px; padding: 40px; animation: fadeInUp 0.5s ease; }
.login-card h1 { font-size: 22px; font-weight: 700; text-align: center; margin-bottom: 28px; letter-spacing: -0.3px; }
.login-card form { display: flex; flex-direction: column; gap: 14px; }
.back-link { background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 13px; text-align: left; padding: 0; margin-bottom: 8px; }
.back-link:hover { color: var(--primary); }
.err { color: var(--danger); font-size: 13px; text-align: center; }
.footer { text-align: center; color: var(--text-muted); font-size: 13px; margin-top: 20px; }
.footer a { color: var(--primary); text-decoration: none; font-weight: 500; }
.footer a:hover { text-decoration: underline; }
</style>
