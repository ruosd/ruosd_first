// 管理员接口 API — 路径前缀 /api/admin
const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const A = (p) => `${API_BASE}/api/admin${p}`

export const adminAPI = {
  async login(username, password) {
    const r = await fetch(A('/login'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || e.message || '登录失败') }
    const d = await r.json()
    localStorage.removeItem('user_token'); localStorage.removeItem('user_info')
    localStorage.setItem('admin_token', d.token); localStorage.setItem('admin_username', d.username)
    return d
  },

  async logout() {
    localStorage.removeItem('admin_token'); localStorage.removeItem('admin_username')
    localStorage.removeItem('user_token'); localStorage.removeItem('user_info')
  },
  isAuthenticated() { return !!localStorage.getItem('admin_token') },
  getAdminUsername() { return localStorage.getItem('admin_username') },

  async getCollections() {
    const r = await fetch(A('/collections'))
    if (!r.ok) throw new Error('获取失败')
    return r.json()
  },
  async getCollectionStats(name) {
    const r = await fetch(A(`/collections/${name}/stats`))
    if (!r.ok) throw new Error('获取失败')
    return r.json()
  },
  async getAllDocuments(name, limit = 50, offset = 0) {
    const r = await fetch(A(`/collections/${name}/documents?limit=${limit}&offset=${offset}`))
    if (!r.ok) throw new Error('获取失败')
    return r.json()
  },
  async searchCollection(name, query, n = 5) {
    const r = await fetch(A(`/collections/${name}/search?query=${encodeURIComponent(query)}&n_results=${n}`))
    if (!r.ok) throw new Error('搜索失败')
    return r.json()
  },
  async getMemoryStats() {
    const r = await fetch(A('/memory/stats'))
    if (!r.ok) throw new Error('获取失败')
    return r.json()
  },
  async getMemoryTypes() {
    const r = await fetch(A('/memory/types'))
    if (!r.ok) throw new Error('获取失败')
    return r.json()
  },
  async queryMemory(text, userId = null, sessionId = null, types = null) {
    const r = await fetch(A('/memory/query'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query_text: text, user_id: userId, session_id: sessionId, memory_types: types, n_results: 5 }),
    })
    if (!r.ok) throw new Error('查询失败')
    return r.json()
  },
  async processDocument(content, docId, type = 'TXT', col = 'knowledge_base') {
    const r = await fetch(A('/documents/process'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, doc_id: docId, doc_type: type, collection_name: col }),
    })
    if (!r.ok) throw new Error('处理失败')
    return r.json()
  },
  async uploadFile(file, col = 'knowledge_base') {
    const fd = new FormData(); fd.append('file', file); fd.append('collection_name', col)
    const r = await fetch(A('/documents/upload'), { method: 'POST', body: fd })
    if (!r.ok) throw new Error('上传失败')
    return r.json()
  },
  async deleteDocuments(col, ids) {
    const r = await fetch(A(`/collections/${col}/documents`), {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids }),
    })
    if (!r.ok) throw new Error('删除失败')
    return r.json()
  },
  async cleanupMemory(type = null, days = 30) {
    const p = new URLSearchParams({ older_than_days: days })
    if (type) p.append('memory_type', type)
    const r = await fetch(A(`/memory/cleanup?${p}`), { method: 'DELETE' })
    if (!r.ok) throw new Error('清理失败')
    return r.json()
  },
  async healthCheck() { return (await fetch(A('/health'))).json() },
}

export default adminAPI
