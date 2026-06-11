import { createRouter, createWebHistory } from 'vue-router'
import AdminLogin from './components/AdminLogin.vue'
import AdminDashboard from './components/AdminDashboard.vue'
import ChatView from './components/ChatView.vue'
import UserLogin from './components/UserLogin.vue'
import UserRegister from './components/UserRegister.vue'
import HomePage from './components/HomePage.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: HomePage,
    meta: { requiresAuth: false }
  },
  {
    path: '/login',
    name: 'UserLogin',
    component: UserLogin,
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'UserRegister',
    component: UserRegister,
    meta: { requiresAuth: false }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: ChatView,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/login',
    name: 'AdminLogin',
    component: AdminLogin,
    meta: { requiresAuth: false }
  },
  {
    path: '/admin/dashboard',
    name: 'AdminDashboard',
    component: AdminDashboard,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin',
    redirect: '/admin/login'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const adminToken = localStorage.getItem('admin_token')
  const userToken = localStorage.getItem('user_token')
  
  if (to.meta.requiresAdmin) {
    // 需要管理员权限
    if (!adminToken) {
      next('/admin/login')
    } else {
      next()
    }
  } else if (to.meta.requiresAuth) {
    // 需要用户登录
    if (!adminToken && !userToken) {
      next('/login')
    } else {
      next()
    }
  } else if (to.path === '/admin/login' && adminToken) {
    // 管理员已登录，访问登录页跳转到控制台
    next('/admin/dashboard')
  } else {
    // 根路径 '/' 和 '/login' 始终显示登录页面，不受登录状态影响
    next()
  }
})

export default router
