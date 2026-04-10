import { useState, useRef, useEffect } from 'react'
import type { Message } from '../App'

interface ChatPanelProps {
  messages: Message[]
  loading: boolean
  onSend: (content: string) => void
}

export default function ChatPanel({ messages, loading, onSend }: ChatPanelProps) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || loading) return
    onSend(trimmed)
    setInput('')
  }

  const suggestions = [
    '今天午餐 30 元',
    '打车花了 45',
    '这个月花了多少',
    '帮我看看餐饮预算',
  ]

  return (
    <div className="flex flex-col" style={{ minHeight: 'calc(100vh - 120px)' }}>
      {/* Messages */}
      <div className="flex-1 overflow-y-auto rounded-xl p-6 space-y-4" style={{ background: 'var(--bg-card)', border: '1px solid var(--border-light)' }}>
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-16">
            <div className="text-5xl mb-4">📒</div>
            <h2 className="mb-2">开始记录你的财务</h2>
            <p className="mb-6 max-w-sm" style={{ color: 'var(--text-secondary)' }}>
              用自然语言告诉助手你的收支情况，或者查询你的财务数据
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              {suggestions.map(s => (
                <button
                  key={s}
                  onClick={() => onSend(s)}
                  className="px-4 py-2 rounded-lg text-sm transition-colors cursor-pointer"
                  style={{
                    background: 'var(--accent-light)',
                    color: 'var(--accent)',
                    border: '1px solid transparent',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = 'var(--accent)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = 'transparent'
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map(msg => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className="max-w-lg px-4 py-3 rounded-xl text-sm"
                  style={{
                    background: msg.role === 'user'
                      ? 'var(--accent)'
                      : 'var(--bg)',
                    color: msg.role === 'user' ? '#fff' : 'var(--text-primary)',
                    boxShadow: 'var(--shadow)',
                  }}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  <p
                    className="text-xs mt-1.5"
                    style={{
                      opacity: msg.role === 'user' ? 0.8 : 1,
                      color: msg.role === 'user' ? 'rgba(255,255,255,0.8)' : 'var(--text-muted)',
                    }}
                  >
                    {msg.timestamp.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                    {msg.trace_id && ` · ${msg.trace_id.slice(0, 8)}`}
                  </p>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div
                  className="px-4 py-3 rounded-xl text-sm"
                  style={{ background: 'var(--bg)', boxShadow: 'var(--shadow)' }}
                >
                  <div className="flex gap-1.5">
                    <span className="w-2 h-2 rounded-full animate-bounce" style={{ background: 'var(--text-muted)', animationDelay: '0ms' }} />
                    <span className="w-2 h-2 rounded-full animate-bounce" style={{ background: 'var(--text-muted)', animationDelay: '150ms' }} />
                    <span className="w-2 h-2 rounded-full animate-bounce" style={{ background: 'var(--text-muted)', animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="mt-4 flex gap-3">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="输入你的收支情况或查询..."
          className="flex-1 px-4 py-3 rounded-xl text-sm outline-none transition-shadow"
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
          }}
          onFocus={e => {
            e.currentTarget.style.borderColor = 'var(--accent)'
          }}
          onBlur={e => {
            e.currentTarget.style.borderColor = 'var(--border)'
          }}
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-6 py-3 rounded-xl text-sm font-medium text-white transition-opacity cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ background: 'var(--accent)' }}
          onMouseEnter={e => {
            if (!loading && input.trim()) e.currentTarget.style.opacity = '0.85'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.opacity = '1'
          }}
        >
          发送
        </button>
      </form>
    </div>
  )
}
