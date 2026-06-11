<template>
  <div class="database-viewer">
    <h2>数据库查看器</h2>
    <p class="description">查看ChromaDB向量数据库中的集合和文档</p>

    <div class="controls">
      <button @click="loadCollections" class="btn btn-sm btn-secondary">
        🔄 刷新列表
      </button>
    </div>

    <!-- 集合列表 -->
    <div class="collections-section">
      <h3>集合列表</h3>
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="collections.length === 0" class="empty">
        暂无集合数据
      </div>
      <div v-else class="collections-grid">
        <div
          v-for="collection in collections"
          :key="collection"
          :class="['collection-card', { active: selectedCollection === collection }]"
          @click="selectCollection(collection)"
        >
          <div class="collection-icon">📊</div>
          <div class="collection-name">{{ collection }}</div>
        </div>
      </div>
    </div>

    <!-- 选中集合详情 -->
    <div v-if="selectedCollection" class="collection-detail">
      <h3>集合详情: {{ selectedCollection }}</h3>

      <!-- 统计信息 -->
      <div v-if="collectionStats" class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">{{ collectionStats.document_count || 0 }}</div>
          <div class="stat-label">文档数量</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ collectionStats.embedding_dimension || 0 }}</div>
          <div class="stat-label">向量维度</div>
        </div>
      </div>

      <!-- 搜索功能 -->
      <div class="search-section">
        <h4>搜索文档</h4>
        <div class="search-form">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="输入搜索关键词..."
            @keyup.enter="searchDocuments"
          />
          <button @click="searchDocuments" :disabled="!searchQuery || searching">
            {{ searching ? '搜索中...' : '搜索' }}
          </button>
        </div>
      </div>

      <!-- 搜索结果 -->
      <div v-if="searchResults.length > 0" class="search-results">
        <h4>搜索结果 ({{ searchResults.length }})</h4>
        <div class="results-list">
          <div
            v-for="(result, index) in searchResults"
            :key="index"
            class="result-item"
          >
            <div class="result-header">
              <span class="result-index">#{{ index + 1 }}</span>
              <span class="result-distance">距离: {{ result.distance }}</span>
              <button
              v-if="result.chunk_id"
              @click="deleteDocument(result.chunk_id)"
              class="delete-btn"
            >
              删除
            </button>
          </div>
          <div class="result-content">{{ result.content }}</div>
          <div v-if="result.parent_section" class="result-meta">
            所属章节: {{ result.parent_section }}
          </div>
          <div v-if="result.metadata" class="result-metadata">
            <span v-for="(value, key) in result.metadata" :key="key" class="meta-tag">
              {{ key }}: {{ value }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 浏览所有文档 -->
    <div class="browse-section">
      <div class="section-header">
        <h4>全部文档 (共 {{ totalDocuments }} 条)</h4>
      </div>
      
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="allDocuments.length === 0" class="empty">
        该集合暂无文档
      </div>
      <div v-else class="documents-list">
        <div
          v-for="doc in displayedDocuments"
          :key="doc.chunk_id"
          class="document-item"
        >
          <div class="doc-header">
            <span class="doc-id">{{ doc.chunk_id }}</span>
            <button @click="deleteDocument(doc.chunk_id)" class="delete-btn">
              删除
            </button>
          </div>
          <div class="doc-content">{{ truncateText(doc.content, 300) }}</div>
          <div v-if="doc.metadata && Object.keys(doc.metadata).length > 0" class="doc-metadata">
            <span v-for="(value, key) in doc.metadata" :key="key" class="meta-tag">
              {{ key }}: {{ value }}
            </span>
          </div>
        </div>
      </div>

      <!-- 分页控件 -->
      <div v-if="totalPages > 1" class="pagination">
        <button @click="prevPage" :disabled="currentPage === 1" class="page-btn">
          ← 上一页
        </button>
        <div class="page-info">
          第 {{ currentPage }} / {{ totalPages }} 页
        </div>
        <button @click="nextPage" :disabled="currentPage === totalPages" class="page-btn">
          下一页 →
        </button>
      </div>
    </div>
  </div>

    <!-- 删除确认弹窗 -->
    <div v-if="showDeleteConfirm" class="modal-overlay" @click="showDeleteConfirm = false">
      <div class="modal" @click.stop>
        <h3>确认删除</h3>
        <p>确定要删除文档 <strong>{{ documentToDelete }}</strong> 吗？</p>
        <div class="modal-actions">
          <button @click="showDeleteConfirm = false" class="btn btn-sm btn-secondary">取消</button>
          <button @click="confirmDelete" class="btn btn-sm btn-danger">确认删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { adminAPI } from '../api/admin.js'

const loading = ref(false)
const searching = ref(false)
const collections = ref([])
const selectedCollection = ref(null)
const collectionStats = ref(null)
const searchQuery = ref('')
const searchResults = ref([])
const allDocuments = ref([])

// 分页参数
const currentPage = ref(1)
const pageSize = ref(20)
const totalDocuments = ref(0)

const showDeleteConfirm = ref(false)
const documentToDelete = ref('')

// 计算分页信息
const totalPages = computed(() => {
  return Math.ceil(totalDocuments.value / pageSize.value)
})

const displayedDocuments = computed(() => {
  return allDocuments.value
})

const loadCollections = async () => {
  loading.value = true
  try {
    const response = await adminAPI.getCollections()
    collections.value = response.collections || []
  } catch (error) {
    console.error('加载集合列表失败:', error)
  } finally {
    loading.value = false
  }
}

const selectCollection = async (collection) => {
  selectedCollection.value = collection
  searchQuery.value = ''
  searchResults.value = []
  currentPage.value = 1

  try {
    const response = await adminAPI.getCollectionStats(collection)
    collectionStats.value = response.data

    // 加载第一页文档
    await loadDocuments(1)
  } catch (error) {
    console.error('加载集合详情失败:', error)
  }
}

const loadDocuments = async (page) => {
  if (!selectedCollection.value) return

  loading.value = true
  try {
    const offset = (page - 1) * pageSize.value
    const response = await adminAPI.getAllDocuments(
      selectedCollection.value,
      pageSize.value,
      offset
    )
    allDocuments.value = response.documents || []
    totalDocuments.value = response.total_count || 0
    currentPage.value = page
  } catch (error) {
    console.error('加载文档失败:', error)
  } finally {
    loading.value = false
  }
}

const goToPage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    loadDocuments(page)
  }
}

const prevPage = () => {
  if (currentPage.value > 1) {
    loadDocuments(currentPage.value - 1)
  }
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    loadDocuments(currentPage.value + 1)
  }
}

const searchDocuments = async () => {
  if (!searchQuery.value || !selectedCollection.value) return

  searching.value = true
  try {
    const response = await adminAPI.searchCollection(
      selectedCollection.value,
      searchQuery.value,
      10
    )
    searchResults.value = response.results || []
  } catch (error) {
    console.error('搜索失败:', error)
  } finally {
    searching.value = false
  }
}

const loadMore = () => {
  displayedCount.value += 10
}

const deleteDocument = (chunkId) => {
  documentToDelete.value = chunkId
  showDeleteConfirm.value = true
}

const confirmDelete = async () => {
  try {
    await adminAPI.deleteDocuments(selectedCollection.value, [documentToDelete.value])
    // 刷新列表
    await selectCollection(selectedCollection.value)
    showDeleteConfirm.value = false
    documentToDelete.value = ''
  } catch (error) {
    console.error('删除文档失败:', error)
    alert('删除失败: ' + error.message)
  }
}

const truncateText = (text, maxLength) => {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

// 初始化加载
loadCollections()
</script>

<style scoped>
.database-viewer { padding: 0; }
.database-viewer h2 { font-size: 20px; font-weight: 700; margin-bottom: 4px; color: var(--text); }
.description { color: var(--text-secondary); font-size: 14px; margin-bottom: 24px; }
.controls { margin-bottom: 24px; }

.collections-section { margin-bottom: 32px; }
.collections-section h3 { margin-bottom: 16px; color: var(--text); font-size: 16px; font-weight: 600; }
.loading, .empty { text-align: center; padding: 60px; color: var(--text-muted); font-size: 14px; }

.collections-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.collection-card {
  padding: 24px 20px; background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius); cursor: pointer; transition: all var(--transition); text-align: center;
}
.collection-card:hover { border-color: var(--primary); transform: translateY(-2px); box-shadow: var(--shadow-md); }
.collection-card.active { border-color: var(--primary); background: var(--primary-bg); }
.collection-icon { font-size: 32px; margin-bottom: 8px; }
.collection-name { font-weight: 500; color: var(--text); font-size: 13px; }

.collection-detail {
  margin-top: 32px;
}

.collection-detail h3 {
  margin-bottom: 16px;
  color: #333;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  opacity: 0.9;
}

.search-section {
  margin-bottom: 24px;
}

.search-section h4 {
  margin-bottom: 12px;
  color: #333;
}

.search-form {
  display: flex;
  gap: 12px;
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
  margin-bottom: 24px;
}

.search-results h4 {
  margin-bottom: 12px;
  color: #333;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-item {
  background: #f9f9f9;
  padding: 16px;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.result-index {
  font-weight: bold;
  color: #667eea;
}

.result-distance {
  font-size: 12px;
  color: #999;
}

.delete-btn {
  padding: 4px 10px;
  background: linear-gradient(135deg, #f56565 0%, #c53030 100%);
  color: #fff; border: none; border-radius: 5px;
  cursor: pointer; font-size: 11px; font-weight: 500;
  transition: all 0.2s;
}
.delete-btn:hover { opacity: 0.9; transform: scale(1.05); }

.result-content {
  color: #555;
  line-height: 1.6;
  margin-bottom: 8px;
}

.result-meta {
  font-size: 12px;
  color: #667eea;
  margin-bottom: 8px;
}

.result-metadata {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.meta-tag {
  padding: 4px 8px;
  background: #eef;
  color: #339;
  border-radius: 4px;
  font-size: 12px;
}

.browse-section {
  margin-top: 32px;
}

.browse-section h4 {
  margin-bottom: 16px;
  color: #333;
}

.documents-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.document-item {
  background: white;
  padding: 16px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.doc-id {
  font-weight: 500;
  color: #667eea;
  font-size: 14px;
}

.doc-content {
  color: #555;
  line-height: 1.6;
  font-size: 14px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
  padding: 16px;
  background: #f9f9f9;
  border-radius: 8px;
}

.page-btn {
  padding: 8px 16px; background: #fff; border: 1px solid #e0e0e0;
  border-radius: 7px; cursor: pointer; font-size: 13px; color: #555;
  transition: all 0.2s; font-weight: 500;
}
.page-btn:hover:not(:disabled) { border-color: #667eea; color: #667eea; }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.page-info {
  font-size: 14px;
  color: #666;
  min-width: 100px;
  text-align: center;
}

.doc-metadata {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.load-more-btn {
  width: 100%;
  padding: 12px;
  background: #f0f0f0;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
  margin-top: 16px;
  font-size: 14px;
}

.load-more-btn:hover {
  background: #e0e0e0;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  padding: 24px;
  border-radius: 12px;
  max-width: 400px;
  width: 90%;
}

.modal h3 {
  margin-bottom: 12px;
  color: #333;
}

.modal p {
  margin-bottom: 20px;
  color: #555;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.cancel-btn,
.confirm-btn {
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.cancel-btn {
  background: #f0f0f0;
  border: 1px solid #ddd;
  color: #333;
}

.confirm-btn {
  background: #c33;
  border: 1px solid #c33;
  color: white;
}

.confirm-btn:hover {
  background: #a22;
}
</style>
