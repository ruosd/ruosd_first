<template>
  <div class="admin">
    <nav class="top-nav">
      <div class="nav-brand"><span class="dot"></span>管理控制台</div>
      <div class="nav-center">
        <button v-for="tab in tabs" :key="tab.id"
          :class="['tab-btn', { active: activeTab === tab.id }]"
          @click="activeTab = tab.id">
          {{ tab.icon }} {{ tab.label }}
        </button>
      </div>
      <div class="nav-actions">
        <button @click="$router.push('/chat')" class="btn btn-sm btn-ghost">返回对话</button>
        <button @click="handleLogout" class="btn btn-sm btn-ghost">退出</button>
      </div>
    </nav>

    <div class="admin-body">
      <KnowledgeUpload v-if="activeTab === 'upload'" />
      <MemoryViewer v-else-if="activeTab === 'memory'" />
      <DatabaseViewer v-else-if="activeTab === 'database'" />
      <SqlViewer v-else-if="activeTab === 'sql'" />
      <SystemSettings v-else-if="activeTab === 'settings'" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'; import { useRouter } from 'vue-router'; import { adminAPI } from '../api/admin.js'
import KnowledgeUpload from './KnowledgeUpload.vue'
import DatabaseViewer from './DatabaseViewer.vue'
import MemoryViewer from './MemoryViewer.vue'
import SystemSettings from './SystemSettings.vue'
import SqlViewer from './SqlViewer.vue'

const router = useRouter()
const activeTab = ref('upload')
const tabs = [
  { id: 'upload', label: '知识上传', icon: '📤' },
  { id: 'memory', label: '记忆管理', icon: '🧠' },
  { id: 'database', label: '向量数据库', icon: '🗄' },
  { id: 'sql', label: 'SQL 数据', icon: '🗃' },
  { id: 'settings', label: '设置', icon: '⚙' },
]

const handleLogout = () => { adminAPI.logout(); router.push('/admin/login') }
onMounted(() => { if (!adminAPI.isAuthenticated()) router.push('/admin/login') })
</script>

<style scoped>
.admin { min-height: 100vh; background: var(--bg); }
.admin-body { max-width: 960px; margin: 0 auto; padding: 32px 24px; }
.tab-btn {
  padding: 6px 16px; border: none; background: transparent; color: var(--text-secondary);
  font-size: 13px; font-weight: 500; cursor: pointer; border-radius: 6px; transition: all var(--transition);
}
.tab-btn:hover { background: var(--border-light); color: var(--text); }
.tab-btn.active { background: var(--primary-bg); color: var(--primary); }
</style>
