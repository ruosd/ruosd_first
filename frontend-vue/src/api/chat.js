import axios from 'axios'

// 在 Docker 环境下通过 nginx 反向代理访问，使用相对路径即可
const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

// 创建会话
export async function createConversation() {
  const response = await axios.post(`${API_BASE}/api/chat/conversation`)
  return response.data
}

// 发送消息（流式）
export function sendMessageStream(sessionId, message, currentAgent, onChunk, onComplete, onError) {
  const formData = new FormData()
  formData.append('session_id', sessionId)
  formData.append('message', message)
  if (currentAgent) {
    formData.append('current_agent', currentAgent)
  }

  const eventSource = new EventSource(`${API_BASE}/api/chat/message/stream?sid=${sessionId}&msg=${encodeURIComponent(message)}&agent=${currentAgent || ''}`)
  
  let fullResponse = ''
  let agentName = ''

  eventSource.onmessage = (event) => {
    const data = event.data
    
    if (data.startsWith('data: ')) {
      const content = data.substring(6)
      
      // 检查是否是结束标记
      if (content.startsWith('[END]|')) {
        const parts = content.split('|')
        agentName = parts[1]
        const newSessionId = parts[2]
        onComplete(fullResponse, agentName, newSessionId)
        eventSource.close()
        return
      }
      
      fullResponse += content
      onChunk(fullResponse)
    }
  }

  eventSource.onerror = (error) => {
    eventSource.close()
    onError(error)
  }

  // 使用 fetch API 实现流式请求
  return {
    abort: () => eventSource.close()
  }
}

// 发送消息（普通）
export async function sendMessage(sessionId, message, currentAgent) {
  const response = await axios.post(`${API_BASE}/api/chat/message`, {
    session_id: sessionId,
    message: message,
    current_agent: currentAgent
  })
  return response.data
}

// 发送流式消息（使用 fetch）
export async function sendMessageStreamFetch(sessionId, message, currentAgent, onChunk, onComplete, onError) {
  try {
    const response = await fetch(`${API_BASE}/api/chat/message/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        session_id: sessionId,
        message: message,
        current_agent: currentAgent
      })
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let fullResponse = ''
    let agentName = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n')

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const content = line.substring(6)
          
          // 检查是否是结束标记
          if (content.startsWith('[END]|')) {
            const parts = content.split('|')
            agentName = parts[1]
            const newSessionId = parts[2]
            onComplete(fullResponse, agentName, newSessionId)
            return { fullResponse, agentName }
          }
          
          fullResponse += content
          onChunk(fullResponse)
        }
      }
    }

    return { fullResponse, agentName }
  } catch (error) {
    onError(error)
    throw error
  }
}

// 获取对话历史
export async function getConversationHistory(sessionId) {
  const response = await axios.get(`${API_BASE}/api/chat/history/${sessionId}`)
  return response.data
}

// 删除会话
export async function deleteConversation(sessionId) {
  const response = await axios.delete(`${API_BASE}/api/chat/conversation/${sessionId}`)
  return response.data
}

// 获取系统信息
export async function getSystemInfo() {
  const response = await axios.get(`${API_BASE}/system/info`)
  return response.data
}
