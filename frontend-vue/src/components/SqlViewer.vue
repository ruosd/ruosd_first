<template>
  <div class="sql-viewer">
    <h2>🗃 SQL 数据库查看</h2>
    <p>查看 MySQL 订单和用户数据、产品数据、Redis 活跃会话</p>

    <!-- 切换 -->
    <div class="tab-row">
      <button v-for="t in tabs" :key="t.id"
        :class="['tab', { active: activeTab === t.id }]"
        @click="activeTab = t.id; loadData()">
        {{ t.label }}
      </button>
    </div>

    <!-- 用户 -->
    <div v-if="activeTab === 'users'" class="section">
      <div class="toolbar">
        <span>共 {{ users.length }} 条</span>
        <button @click="loadData" class="btn btn-sm btn-secondary">刷新</button>
      </div>
      <table v-if="users.length">
        <thead><tr><th>ID</th><th>用户名</th><th>邮箱</th><th>昵称</th><th>角色</th><th>注册时间</th></tr></thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.id }}</td><td>{{ u.username }}</td><td>{{ u.email }}</td>
            <td>{{ u.nickname }}</td><td>{{ u.role }}</td><td>{{ u.created_at }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">暂无数据</div>
    </div>

    <!-- 订单 -->
    <div v-if="activeTab === 'orders'" class="section">
      <div class="toolbar">
        <span>共 {{ orders.length }} 条</span>
        <button @click="loadData" class="btn btn-sm btn-secondary">刷新</button>
      </div>
      <table v-if="orders.length">
        <thead><tr><th>订单号</th><th>用户</th><th>状态</th><th>金额</th><th>时间</th></tr></thead>
        <tbody>
          <tr v-for="o in orders" :key="o.order_id">
            <td class="mono">{{ o.order_id }}</td>
            <td>{{ o.user_id }}</td>
            <td><span :class="['status', o.status]">{{ o.status }}</span></td>
            <td>¥{{ o.total_amount }}</td>
            <td class="mono">{{ o.created_at }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">暂无数据</div>
    </div>

    <!-- 产品 -->
    <div v-if="activeTab === 'products'" class="section">
      <div class="toolbar">
        <span>共 {{ products.length }} 条</span>
        <button @click="loadData" class="btn btn-sm btn-secondary">刷新</button>
      </div>
      <table v-if="products.length">
        <thead><tr><th>ID</th><th>名称</th><th>分类</th><th>价格</th><th>库存</th><th>描述</th></tr></thead>
        <tbody>
          <tr v-for="p in products" :key="p.id">
            <td>{{ p.id }}</td><td>{{ p.name }}</td><td>{{ p.category }}</td>
            <td>¥{{ p.price }}</td><td>{{ p.stock }}</td>
            <td class="desc">{{ p.description }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">暂无数据</div>
    </div>

    <!-- 会话 -->
    <div v-if="activeTab === 'conversations'" class="section">
      <div class="toolbar">
        <span>共 {{ conversations.length }} 条</span>
        <button @click="loadData" class="btn btn-sm btn-secondary">刷新</button>
      </div>
      <table v-if="conversations.length">
        <thead><tr><th>会话ID</th><th>用户</th><th>创建时间</th></tr></thead>
        <tbody>
          <tr v-for="c in conversations" :key="c.session_id">
            <td class="mono">{{ c.session_id }}</td>
            <td>{{ c.user_id || '游客' }}</td>
            <td class="mono">{{ c.created_at }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">暂无数据</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const activeTab = ref('orders')
const tabs = [
  { id: 'orders', label: '📦 订单 (MySQL)' },
  { id: 'users', label: '👤 用户 (MySQL)' },
  { id: 'products', label: '📱 产品 (MySQL)' },
  { id: 'conversations', label: '💬 会话 (Redis)' },
]
const users = ref([])
const orders = ref([])
const products = ref([])
const conversations = ref([])

async function loadData() {
  const base = import.meta.env.VITE_API_BASE_URL || ''
  try {
    if (activeTab.value === 'users') {
      const r = await fetch(`${base}/api/admin/sql/users`)
      const d = await r.json()
      users.value = d.users || []
    } else if (activeTab.value === 'orders') {
      const r = await fetch(`${base}/api/admin/sql/orders`)
      const d = await r.json()
      orders.value = d.orders || []
    } else if (activeTab.value === 'products') {
      const r = await fetch(`${base}/api/admin/sql/products`)
      const d = await r.json()
      products.value = d.products || []
    } else {
      const r = await fetch(`${base}/api/admin/sql/conversations`)
      const d = await r.json()
      conversations.value = d.conversations || []
    }
  } catch (e) { console.error(e) }
}

onMounted(loadData)
</script>

<style scoped>
.sql-viewer { max-width: 960px; margin: 0 auto; }
.sql-viewer h2 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
.sql-viewer > p { color: var(--text-secondary); font-size: 14px; margin-bottom: 20px; }
.tab-row { display: flex; gap: 8px; margin-bottom: 20px; }
.tab {
  padding: 8px 16px; border: 1px solid var(--border); border-radius: 8px;
  background: var(--surface); cursor: pointer; font-size: 13px; transition: all 0.2s;
}
.tab:hover { border-color: var(--primary); }
.tab.active { background: var(--primary); color: #fff; border-color: var(--primary); }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; font-size: 13px; color: var(--text-secondary); }
table { width: 100%; border-collapse: collapse; background: var(--surface); border-radius: var(--radius); overflow: hidden; }
th { padding: 10px 12px; text-align: left; background: var(--border-light); font-size: 12px; color: var(--text-secondary); font-weight: 600; }
td { padding: 10px 12px; border-bottom: 1px solid var(--border-light); font-size: 13px; }
.mono { font-family: 'SF Mono', Monaco, monospace; font-size: 12px; }
.desc { max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.status { padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; }
.status.待付款 { background: #fff7ed; color: #ea580c; }
.status.待发货 { background: #fefce8; color: #ca8a04; }
.status.已发货 { background: #eff6ff; color: #2563eb; }
.status.已送达 { background: #f0fdf4; color: #16a34a; }
.status.已完成 { background: #ecfdf5; color: #059669; }
.status.退款中 { background: #fef2f2; color: #dc2626; }
.status.已退款 { background: #f9fafb; color: #6b7280; }
.empty { text-align: center; padding: 60px; color: var(--text-muted); }
</style>
