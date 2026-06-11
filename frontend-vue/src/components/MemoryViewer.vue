<template>
  <div class="memory-viewer">
    <h2>记忆管理系统</h2>
    <p class="description">查看和管理Agent记忆系统中的数据</p>

    <!-- 记忆统计 -->
    <div class="memory-stats">
      <h3>记忆统计</h3>
      <div class="stats-grid">
        <div
          v-for="type in memoryTypes"
          :key="type.name"
          class="type-stat-card"
          @click="selectMemoryType(type.name)"
          :class="{ active: selectedType === type.name }"
        >
          <div class="type-icon">{{ type.icon }}</div>
          <div class="type-info">
            <div class="type-name">{{ type.label }}</div>
            <div class="type-count">{{ getTypeCount(type.name) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 记忆检索 -->
    <div class="memory-search">
      <h3>记忆检索</h3>
      <div class="search-form">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="输入关键词检索记忆..."
          @keyup.enter="searchMemory"
        />
        <button @click="searchMemory" :disabled="!searchQuery || searching">
          {{ searching ? '检索中...' : '检索' }}
        </button>
      </div>

      <div v-if="searchResults" class="search-results">
        <h4>检索结果</h4>
        <div class="results-content">
          {{ searchResults }}
        </div>
      </div>
    </div>

    <!-- 记忆清理 -->
    <div class="memory-cleanup">
      <h3>记忆清理</h3>
      <div class="cleanup-form">
        <label>
          <input v-model.number="cleanupDays" type="number" min="1" max="365" />
          天前的记忆
        </label>
        <button @click="cleanupMemory" class="btn btn-danger btn-sm">
          🗑️ 清理过期记忆
        </button>
      </div>
      <div v-if="cleanupMessage" :class="['cleanup-message', cleanupMessage.type]">
        {{ cleanupMessage.text }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { adminAPI } from '../api/admin.js'

const memoryTypes = [
  { name: 'SHORT_TERM', label: '短期记忆', icon: '⚡' },
  { name: 'LONG_TERM', label: '长期记忆', icon: '💾' },
  { name: 'KNOWLEDGE', label: '知识库', icon: '📚' },
  { name: 'PRODUCT', label: '产品记忆', icon: '🏷️' }
]

const selectedType = ref(null)
const searchQuery = ref('')
const searching = ref(false)
const searchResults = ref('')
const cleanupDays = ref(30)
const cleanupMessage = ref(null)
const typeCounts = ref({})

const getTypeCount = (typeName) => {
  return typeCounts.value[typeName] || 0
}

const loadMemoryStats = async () => {
  try {
    const response = await adminAPI.getMemoryStats()
    // 更新各类型计数
    const stats = response.data || {}
    typeCounts.value = {
      SHORT_TERM: stats.short_term_count || 0,
      LONG_TERM: stats.long_term_count || 0,
      KNOWLEDGE: stats.knowledge_count || 0,
      PRODUCT: stats.product_count || 0
    }
  } catch (error) {
    console.error('加载记忆统计失败:', error)
  }
}

const selectMemoryType = async (typeName) => {
  selectedType.value = typeName
  // 检索该类型的记忆
  try {
    const response = await adminAPI.queryMemory(
      '', // 空查询会返回该类型的所有记忆
      null,
      null,
      [typeName]
    )
    searchResults.value = response.context || '暂无记忆'
  } catch (error) {
    console.error('加载记忆失败:', error)
  }
}

const searchMemory = async () => {
  if (!searchQuery.value) return

  searching.value = true
  try {
    const response = await adminAPI.queryMemory(searchQuery.value)
    searchResults.value = response.context || '未找到相关记忆'
  } catch (error) {
    console.error('检索失败:', error)
    searchResults.value = '检索失败: ' + error.message
  } finally {
    searching.value = false
  }
}

const cleanupMemory = async () => {
  try {
    const response = await adminAPI.cleanupMemory(null, cleanupDays.value)
    cleanupMessage.value = {
      type: 'success',
      text: response.message
    }
    // 刷新统计
    loadMemoryStats()
  } catch (error) {
    cleanupMessage.value = {
      type: 'error',
      text: '清理失败: ' + error.message
    }
  }
}

onMounted(() => {
  loadMemoryStats()
})
</script>

<style scoped>
.memory-viewer {
  padding: 24px;
}

.memory-viewer h2 {
  font-size: 24px;
  margin-bottom: 8px;
  color: #333;
}

.description {
  color: #666;
  margin-bottom: 24px;
}

.memory-stats {
  margin-bottom: 32px;
}

.memory-stats h3,
.memory-search h3,
.memory-cleanup h3 {
  margin-bottom: 16px;
  color: #333;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.type-stat-card {
  background: var(--surface); padding: 20px; border-radius: var(--radius);
  border: 1px solid var(--border); cursor: pointer;
  display: flex; align-items: center; gap: 16px; transition: all var(--transition);
}
.type-stat-card:hover { border-color: var(--primary); transform: translateY(-2px); box-shadow: var(--shadow-md); }
.type-stat-card.active { border-color: var(--primary); background: var(--primary-bg); }

.type-icon {
  font-size: 36px;
}

.type-name {
  font-size: 14px;
  color: #666;
  margin-bottom: 4px;
}

.type-count {
  font-size: 24px;
  font-weight: bold;
  color: #333;
}

.memory-search {
  margin-bottom: 32px;
}

.search-form {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.search-form input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.search-form button {
  padding: 9px 18px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff; border: none; border-radius: 7px; cursor: pointer;
  font-size: 13px; font-weight: 500; transition: all 0.2s;
  box-shadow: 0 2px 6px rgba(102,126,234,0.25);
}
.search-form button:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(102,126,234,0.4); }
.search-form button:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }

.search-results {
  background: white;
  padding: 20px;
  border-radius: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.search-results h4 {
  margin-bottom: 12px;
  color: #333;
}

.results-content {
  color: #555;
  line-height: 1.8;
  white-space: pre-wrap;
}

.memory-cleanup {
  background: white;
  padding: 24px;
  border-radius: 8px;
}

.cleanup-form {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.cleanup-form label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #555;
}

.cleanup-form input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  width: 80px;
  text-align: center;
}

.cleanup-message {
  padding: 12px;
  border-radius: 6px;
  text-align: center;
  font-size: 14px;
}

.cleanup-message.success {
  background: #efe;
  color: #383;
  border: 1px solid #cfc;
}

.cleanup-message.error {
  background: #fee;
  color: #c33;
  border: 1px solid #fcc;
}
</style>
