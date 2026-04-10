import { useState } from 'react'
import { chat } from './api/client'
import Header from './components/Header'
import ChatPanel from './components/ChatPanel'
import SummaryPanel from './components/SummaryPanel'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  trace_id?: string
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)

  const userId = 'default_user'

  const handleSend = async (content: string) => {
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const resp = await chat({ user_id: userId, message: content })
      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: resp.answer,
        timestamp: new Date(),
        trace_id: resp.trace_id,
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err) {
      const msg = err instanceof Error ? err.message : '请求失败，请稍后再试'
      const errMsg: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `⚠️ ${msg}`,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errMsg])
    } finally {
      setLoading(false)
    }
  }

  const clearHistory = () => {
    setMessages([])
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header messageCount={messages.length} onClear={clearHistory} />
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6 grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
        <ChatPanel
          messages={messages}
          loading={loading}
          onSend={handleSend}
        />
        <SummaryPanel messages={messages} />
      </main>
    </div>
  )
}

export default App
