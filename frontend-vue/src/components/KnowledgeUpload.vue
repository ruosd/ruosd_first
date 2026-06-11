<template>
  <div class="upload-page">
    <div class="card upload-card">
      <h2>📄 知识库上传</h2>
      <p>上传 TXT 文档，自动分块向量化并导入知识库</p>

      <div class="drop-zone" @dragover.prevent @drop.prevent="handleDrop" @click="$refs.fileInput.click()">
        <input type="file" ref="fileInput" @change="handleFileSelect" accept=".pdf,.txt,.docx" hidden />
        <div v-if="!selectedFile">
          <div class="drop-icon">+</div>
          <p>拖拽文件到此处或点击选择</p>
          <span class="hint">支持 TXT、PDF、DOCX</span>
        </div>
        <div v-else class="file-preview">
          <span class="file-name">{{ selectedFile.name }}</span>
          <span class="file-size">{{ formatSize(selectedFile.size) }}</span>
          <button @click.stop="clearFile" class="btn btn-sm btn-ghost">移除</button>
        </div>
      </div>

      <div class="upload-row">
        <select v-model="collectionName" class="input" style="flex:1">
          <option value="knowledge_base">知识库</option>
          <option value="product_memory">产品记忆</option>
          <option value="short_term_memory">短期记忆</option>
          <option value="long_term_memory">长期记忆</option>
        </select>
        <button @click="uploadFile" :disabled="!selectedFile || uploading" class="btn btn-primary">
          {{ uploading ? '上传中...' : '上传并处理' }}
        </button>
      </div>

      <div v-if="uploadStatus" :class="['status-msg', uploadStatus.type]">{{ uploadStatus.message }}</div>

      <div v-if="uploadResult" class="result-box">
        <div class="result-row"><span>文档ID</span><span>{{ uploadResult.doc_id }}</span></div>
        <div class="result-row"><span>章节数</span><span>{{ uploadResult.sections }}</span></div>
        <div class="result-row"><span>文本块</span><span>{{ uploadResult.chunks }}</span></div>
        <div class="result-row"><span>集合</span><span>{{ uploadResult.collection }}</span></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'; import { adminAPI } from '../api/admin.js'
const fileInput = ref(null); const selectedFile = ref(null); const collectionName = ref('knowledge_base')
const uploading = ref(false); const uploadStatus = ref(null); const uploadResult = ref(null)

const handleFileSelect = (e) => {
  const f = e.target.files[0]; if (f) { selectedFile.value = f; uploadStatus.value = null; uploadResult.value = null }
}
const handleDrop = (e) => {
  const f = e.dataTransfer.files[0]; if (f) selectedFile.value = f
}
const clearFile = () => { selectedFile.value = null; if (fileInput.value) fileInput.value.value = '' }
const formatSize = (b) => b < 1024 ? b + ' B' : (b / 1024).toFixed(1) + ' KB'

const uploadFile = async () => {
  if (!selectedFile.value) return
  uploading.value = true; uploadStatus.value = null; uploadResult.value = null
  try {
    const file = selectedFile.value
    let result
    if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
      const content = await file.text()
      const docId = file.name.replace(/\.[^/.]+$/, '')
      result = await adminAPI.processDocument(content, docId, 'TXT', collectionName.value)
    } else {
      result = await adminAPI.uploadFile(file, collectionName.value)
    }
    uploadResult.value = result
    uploadStatus.value = { type: 'success', message: '上传成功' }
    clearFile()
  } catch (e) {
    uploadStatus.value = { type: 'error', message: e.message || '上传失败' }
  } finally { uploading.value = false }
}
</script>

<style scoped>
.upload-page { max-width: 640px; margin: 0 auto; }
.upload-card { padding: 32px; }
.upload-card h2 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
.upload-card > p { color: var(--text-secondary); font-size: 14px; margin-bottom: 24px; }

.drop-zone {
  border: 2px dashed var(--border); border-radius: var(--radius); padding: 40px;
  text-align: center; cursor: pointer; transition: all var(--transition); margin-bottom: 20px;
}
.drop-zone:hover { border-color: var(--primary); background: var(--primary-bg); }
.drop-icon { font-size: 36px; color: var(--primary); margin-bottom: 8px; font-weight: 200; }
.drop-zone p { color: var(--text-secondary); font-size: 14px; }
.hint { font-size: 12px; color: var(--text-muted); }
.file-preview { display: flex; align-items: center; gap: 12px; justify-content: center; }
.file-name { font-weight: 600; }
.file-size { color: var(--text-muted); font-size: 13px; }

.upload-row { display: flex; gap: 12px; margin-bottom: 16px; }
.status-msg { padding: 12px; border-radius: var(--radius-sm); font-size: 13px; margin-bottom: 16px; }
.status-msg.success { background: var(--success-bg); color: var(--success); }
.status-msg.error { background: var(--danger-bg); color: var(--danger); }

.result-box {
  background: var(--border-light); border-radius: var(--radius); padding: 20px;
}
.result-row { display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px; }
.result-row span:first-child { color: var(--text-secondary); }
.result-row span:last-child { font-weight: 500; font-family: 'SF Mono', Monaco, monospace; font-size: 12px; }
</style>
