import type { ChatRequest, ChatResponse } from './types'

const API_BASE = '/v1'

export async function chat(req: ChatRequest): Promise<ChatResponse> {
  const resp = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${import.meta.env.VITE_API_KEY || ''}`,
    },
    body: JSON.stringify(req),
  })

  if (!resp.ok) {
    if (resp.status === 401) {
      throw new Error('API_KEY 无效或未配置')
    }
    throw new Error(`请求失败: ${resp.status}`)
  }

  return resp.json()
}
