<template>
  <div class="chat-app">
    <!-- 顶部导航 -->
    <nav class="top-nav">
      <div class="nav-brand">
        <span class="dot"></span>电商客服助手
      </div>
      <div class="nav-center">
        <span v-if="currentAgent" class="agent-indicator">{{ currentAgent }}</span>
        <span v-if="sessionId" class="session-id">会话 {{ sessionId.substring(0, 6) }}</span>
      </div>
      <div class="nav-actions">
        <button v-if="isAdmin" @click="goToDashboard" class="btn btn-sm btn-ghost">控制台</button>
        <button @click="handleNewSession" class="btn btn-sm btn-ghost">新会话</button>
        <button @click="handleClearHistory" class="btn btn-sm btn-ghost">清空</button>
        <button @click="handleLogout" class="btn btn-sm btn-ghost">退出</button>
      </div>
    </nav>

    <!-- 消息区 -->
    <main class="chat-main" ref="messagesContainer">
      <div v-if="messages.length === 0" class="welcome">
        <div class="welcome-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
        </div>
        <h2>有什么可以帮您？</h2>
        <p>查询订单、了解产品、物流追踪，直接问我</p>
        <div class="quick-row">
          <button @click="sendQuickQuestion('查询订单状态')" class="quick-chip">📦 查询订单状态</button>
          <button @click="sendQuickQuestion('苹果16多少钱')" class="quick-chip">📱 苹果16多少钱</button>
          <button @click="sendQuickQuestion('配送时间多久')" class="quick-chip">🚚 配送时间多久</button>
          <button @click="sendQuickQuestion('如何申请退款')" class="quick-chip">💳 如何申请退款</button>
        </div>
      </div>

      <div v-for="(msg, index) in messages" :key="index" :class="['msg', msg.role]">
        <div class="msg-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
        <div class="msg-body">
          <div class="msg-meta">
            <span class="msg-sender">{{ msg.role === 'user' ? '我' : '客服助手' }}</span>
            <span v-if="msg.agent" class="msg-agent">{{ msg.agent }}</span>
          </div>
          <div class="msg-text" v-html="formatMsg(msg.content)"></div>
          <div v-if="msg.isStreaming" class="typing"><span></span><span></span><span></span></div>
        </div>
      </div>
    </main>

    <!-- 输入栏 -->
    <footer class="chat-input-bar">
      <div class="input-wrap">
        <textarea
          v-model="inputMessage"
          @keydown.enter.exact.prevent="handleSend"
          placeholder="输入消息，Enter 发送，Shift+Enter 换行"
          :disabled="isLoading"
          rows="1"
        ></textarea>
        <button @click="handleSend" :disabled="!inputMessage.trim() || isLoading" class="send-btn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { createConversation, sendMessageStreamFetch, deleteConversation } from '../api/chat'

const router = useRouter()
const sessionId = ref(null)
const currentAgent = ref(null)
const messages = ref([])
const inputMessage = ref('')
const isLoading = ref(false)
const messagesContainer = ref(null)

const isAdmin = computed(() => !!localStorage.getItem('admin_token'))

const handleLogout = () => {
  localStorage.removeItem('user_token'); localStorage.removeItem('user_info'); localStorage.removeItem('admin_token')
  router.push(isAdmin.value ? '/admin/login' : '/login')
}
const goToDashboard = () => router.push('/admin/dashboard')

async function handleNewSession() {
  try {
    const r = await createConversation()
    sessionId.value = r.session_id; messages.value = []; currentAgent.value = null
  } catch (e) {}
}
async function handleClearHistory() {
  if (sessionId.value) try { await deleteConversation(sessionId.value) } catch (e) {}
  messages.value = []; currentAgent.value = null; sessionId.value = null
}
function sendQuickQuestion(q) { inputMessage.value = q; handleSend() }

async function handleSend() {
  const msg = inputMessage.value.trim()
  if (!msg || isLoading.value) return
  if (!sessionId.value) {
    try { const r = await createConversation(); sessionId.value = r.session_id } catch (e) { return }
  }
  messages.value.push({ role: 'user', content: msg, agent: null })
  inputMessage.value = ''; isLoading.value = true

  const aiIdx = messages.value.length
  messages.value.push({ role: 'assistant', content: '', agent: null, isStreaming: true })
  await nextTick(); scrollBottom()

  try {
    await sendMessageStreamFetch(sessionId.value, msg, currentAgent.value,
      (chunk) => { messages.value[aiIdx].content = chunk; scrollBottom() },
      (full, agent, sid) => {
        messages.value[aiIdx].content = full; messages.value[aiIdx].agent = agent
        messages.value[aiIdx].isStreaming = false; currentAgent.value = agent
        if (sid && sid !== sessionId.value) sessionId.value = sid
        isLoading.value = false
      },
      () => { messages.value[aiIdx].content = '服务暂不可用，请重试'; messages.value[aiIdx].isStreaming = false; isLoading.value = false }
    )
  } catch (e) {
    messages.value[aiIdx].content = '服务暂不可用，请重试'; messages.value[aiIdx].isStreaming = false; isLoading.value = false
  }
}

function scrollBottom() {
  if (messagesContainer.value) messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
}
function formatMsg(c) {
  return c.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\*(.*?)\*/g, '<em>$1</em>')
}
</script>

<style scoped>
.chat-app { display: flex; flex-direction: column; height: 100vh; background: var(--bg); }

/* 导航 */
.top-nav {
  height: 56px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; background: rgba(255,255,255,0.85);
  backdrop-filter: blur(12px); border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.nav-center { display: flex; align-items: center; gap: 12px; }
.agent-indicator {
  font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
  color: var(--primary); background: var(--primary-bg); padding: 3px 10px; border-radius: 20px;
}
.session-id { font-size: 11px; color: var(--text-muted); font-family: 'SF Mono', Monaco, monospace; }

/* 消息区 */
.chat-main {
  flex: 1; overflow-y: auto; padding: 24px;
  max-width: 720px; width: 100%; margin: 0 auto;
}
.welcome { text-align: center; padding: 80px 20px 60px; animation: fadeInUp 0.5s ease; }
.welcome-icon { color: var(--primary); margin-bottom: 16px; opacity: 0.8; }
.welcome h2 { font-size: 22px; font-weight: 600; color: var(--text); margin-bottom: 8px; letter-spacing: -0.3px; }
.welcome p { color: var(--text-secondary); font-size: 15px; margin-bottom: 32px; }
.quick-row { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
.quick-chip {
  padding: 8px 16px; border: 1px solid var(--border); border-radius: 20px;
  background: var(--surface); color: var(--text); font-size: 13px;
  cursor: pointer; transition: all var(--transition);
}
.quick-chip:hover { border-color: var(--primary); color: var(--primary); background: var(--primary-bg); transform: translateY(-1px); }

/* 消息 */
.msg { display: flex; gap: 14px; margin-bottom: 28px; animation: fadeInUp 0.3s ease; }
.msg.user { flex-direction: row-reverse; }
.msg-avatar { width: 34px; height: 34px; border-radius: 50%; background: var(--border-light); display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; }
.msg-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.msg-sender { font-size: 13px; font-weight: 600; color: var(--text); }
.msg-agent { font-size: 10px; padding: 2px 8px; border-radius: 10px; background: var(--primary-bg); color: var(--primary); font-weight: 500; }
.msg.user .msg-meta { flex-direction: row-reverse; text-align: right; }
.msg-text { font-size: 15px; color: var(--text); line-height: 1.7; word-break: break-word; }
.msg.assistant .msg-body { max-width: 100%; }

/* 打字指示器 */
.typing { display: inline-flex; gap: 4px; padding: 6px 0; }
.typing span { width: 6px; height: 6px; border-radius: 50%; background: var(--text-muted); animation: bounce 1.2s infinite ease-in-out; }
.typing span:nth-child(2) { animation-delay: 0.15s; }
.typing span:nth-child(3) { animation-delay: 0.3s; }

/* 输入栏 */
.chat-input-bar { padding: 16px 24px 24px; background: var(--bg); flex-shrink: 0; }
.input-wrap {
  max-width: 720px; margin: 0 auto; display: flex; gap: 10px; align-items: flex-end;
  background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg);
  padding: 6px 6px 6px 18px; box-shadow: var(--shadow-sm); transition: all var(--transition);
}
.input-wrap:focus-within { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(37,99,235,0.08); }
.input-wrap textarea {
  flex: 1; border: none; outline: none; resize: none; font-size: 15px; font-family: inherit;
  color: var(--text); background: transparent; padding: 8px 0; max-height: 120px; line-height: 1.5;
}
.input-wrap textarea::placeholder { color: var(--text-muted); }
.send-btn {
  width: 40px; height: 40px; min-width: 40px; border-radius: 50%;
  background: var(--primary); color: #fff; border: none; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all var(--transition); box-shadow: 0 2px 8px rgba(37,99,235,0.2);
}
.send-btn:hover:not(:disabled) { background: var(--primary-dark); transform: scale(1.05); }
.send-btn:disabled { background: var(--border); box-shadow: none; cursor: not-allowed; }

@keyframes bounce { 0%, 80%, 100% { transform: scale(0.4); } 40% { transform: scale(1); } }
</style>
