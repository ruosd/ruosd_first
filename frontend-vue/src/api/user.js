// 用户接口API
// 在 Docker 环境下通过 nginx 反向代理访问，使用相对路径即可
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export const userAPI = {
  // 用户注册
  async register(username, email, password, nickname = '', phone = '', role = 'user') {
    const response = await fetch(`${API_BASE_URL}/api/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username,
        email,
        password,
        nickname,
        phone,
        role
      }),
    })

    if (!response.ok) {
      let errorMessage = '注册失败'
      try {
        const error = await response.json()
        if (error.detail) {
          errorMessage = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail)
        } else if (error.message) {
          errorMessage = typeof error.message === 'string' ? error.message : JSON.stringify(error.message)
        } else {
          errorMessage = JSON.stringify(error)
        }
      } catch (e) {
        errorMessage = `注册失败 (HTTP ${response.status})`
      }
      throw new Error(errorMessage)
    }

    const data = await response.json()
    // 清除反向 token，防止普通用户和角色混淆
    localStorage.removeItem('user_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_info')
    // 保存 token
    localStorage.setItem('user_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    localStorage.setItem('user_info', JSON.stringify(data.user))
    return data
  },

  // 用户登录
  async login(usernameOrEmail, password) {
    const response = await fetch(`${API_BASE_URL}/api/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username_or_email: usernameOrEmail,
        password: password,
      }),
    })

    if (!response.ok) {
      let errorMessage = '登录失败'
      try {
        const error = await response.json()
        if (error.detail) {
          errorMessage = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail)
        } else if (error.message) {
          errorMessage = typeof error.message === 'string' ? error.message : JSON.stringify(error.message)
        } else {
          errorMessage = JSON.stringify(error)
        }
      } catch (e) {
        errorMessage = `登录失败 (HTTP ${response.status})`
      }
      throw new Error(errorMessage)
    }

    const data = await response.json()
    // 清除管理员 token，防止角色混淆
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_username')
    // 保存用户 token
    localStorage.setItem('user_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    localStorage.setItem('user_info', JSON.stringify(data.user))
    return data
  },

  // 管理员登录
  async adminLogin(usernameOrEmail, password) {
    const response = await fetch(`${API_BASE_URL}/api/login/admin`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username_or_email: usernameOrEmail,
        password: password,
      }),
    })

    if (!response.ok) {
      let errorMessage = '登录失败'
      try {
        const error = await response.json()
        if (error.detail) {
          errorMessage = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail)
        } else if (error.message) {
          errorMessage = typeof error.message === 'string' ? error.message : JSON.stringify(error.message)
        } else {
          errorMessage = JSON.stringify(error)
        }
      } catch (e) {
        errorMessage = `登录失败 (HTTP ${response.status})`
      }
      throw new Error(errorMessage)
    }

    const data = await response.json()
    // 清除反向 token，防止普通用户和角色混淆
    localStorage.removeItem('user_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_info')
    // 保存 token（管理员也用 user_token，后端通过 role 区分）
    localStorage.setItem('user_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    localStorage.setItem('user_info', JSON.stringify(data.user))
    return data
  },

  // 刷新访问令牌
  async refreshAccessToken() {
    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) {
      throw new Error('无刷新令牌')
    }

    const response = await fetch(`${API_BASE_URL}/api/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })

    if (!response.ok) {
      localStorage.removeItem('user_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user_info')
      throw new Error('令牌刷新失败，请重新登录')
    }

    const data = await response.json()
    localStorage.setItem('user_token', data.access_token)
    return data.access_token
  },

  // 退出登录
  async logout() {
    const refreshToken = localStorage.getItem('refresh_token')
    try {
      const token = localStorage.getItem('user_token')
      if (token) {
        const body = {}
        if (refreshToken) {
          body.refresh_token = refreshToken
        }
        await fetch(`${API_BASE_URL}/api/logout`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify(body),
        })
      }
    } catch (e) {
      // 即使服务端登出失败，也清除本地状态
    }
    localStorage.removeItem('user_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_info')
  },

  // 判断是否已登录
  isAuthenticated() {
    return !!localStorage.getItem('user_token')
  },

  // 获取当前用户信息
  getUserInfo() {
    const userInfo = localStorage.getItem('user_info')
    return userInfo ? JSON.parse(userInfo) : null
  },

  // 获取当前用户角色
  getUserRole() {
    const userInfo = this.getUserInfo()
    return userInfo ? userInfo.role : 'guest'
  },

  // 判断是否为管理员
  isAdmin() {
    return this.getUserRole() === 'admin'
  },

  // 获取当前用户详情
  async getCurrentUser() {
    const response = await fetch(`${API_BASE_URL}/api/user/me`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('user_token')}`,
      },
    })

    if (!response.ok) {
      throw new Error('获取用户信息失败')
    }

    return await response.json()
  },

  // 更新用户信息
  async updateUserInfo(nickname = null, phone = null, avatar = null) {
    const data = {}
    if (nickname !== null) data.nickname = nickname
    if (phone !== null) data.phone = phone
    if (avatar !== null) data.avatar = avatar

    const response = await fetch(`${API_BASE_URL}/api/user/me`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('user_token')}`,
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      let errorMessage = '更新失败'
      try {
        const error = await response.json()
        if (error.detail) {
          errorMessage = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail)
        }
      } catch (e) {
        errorMessage = `更新失败 (HTTP ${response.status})`
      }
      throw new Error(errorMessage)
    }

    return await response.json()
  },

  // 修改密码
  async changePassword(oldPassword, newPassword) {
    const response = await fetch(`${API_BASE_URL}/api/user/me/password`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('user_token')}`,
      },
      body: JSON.stringify({
        old_password: oldPassword,
        new_password: newPassword,
      }),
    })

    if (!response.ok) {
      let errorMessage = '修改密码失败'
      try {
        const error = await response.json()
        if (error.detail) {
          errorMessage = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail)
        }
      } catch (e) {
        errorMessage = `修改密码失败 (HTTP ${response.status})`
      }
      throw new Error(errorMessage)
    }

    return await response.json()
  },

  // 获取用户列表（管理员）
  async getUsers(role = null) {
    let url = `${API_BASE_URL}/api/users`
    if (role) {
      url += `?role=${role}`
    }

    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('user_token')}`,
      },
    })

    if (!response.ok) {
      throw new Error('获取用户列表失败')
    }

    return await response.json()
  },

  // 获取单个用户详情
  async getUserById(userId) {
    const response = await fetch(`${API_BASE_URL}/api/users/${userId}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('user_token')}`,
      },
    })

    if (!response.ok) {
      throw new Error('获取用户信息失败')
    }

    return await response.json()
  },

  // 删除用户（管理员）
  async deleteUser(userId) {
    const response = await fetch(`${API_BASE_URL}/api/users/${userId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('user_token')}`,
      },
    })

    if (!response.ok) {
      let errorMessage = '删除失败'
      try {
        const error = await response.json()
        if (error.detail) {
          errorMessage = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail)
        }
      } catch (e) {
        errorMessage = `删除失败 (HTTP ${response.status})`
      }
      throw new Error(errorMessage)
    }

    return await response.json()
  }
}

export default userAPI