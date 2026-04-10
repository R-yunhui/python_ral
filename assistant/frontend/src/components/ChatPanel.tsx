import { useState, useRef, useEffect, type KeyboardEvent } from 'react'
import type { Message } from '../App'

interface ChatPanelProps {
  messages: Message[]
  loading: boolean
  onSend: (content: string) => void
}

const SUGGESTIONS = [
  '今天午餐 30 元',
  '打车花了 45',
  '这个月花了多少',
  '帮我看看餐饮预算',
]

export default function ChatPanel({ messages, loading, onSend }: ChatPanelProps) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = () => {
    const trimmed = input.trim()
    if (!trimmed || loading) return
    onSend(trimmed)
    setInput('')
  }

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* 消息区域 */}
      <div className="flex-1 min-h-0 overflow-y-auto rounded-[var(--radius-lg)] bg-[var(--bg-card)] border border-[var(--border-light)] shadow-[var(--shadow)]">

        {/* 空状态 */}
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center min-h-[440px] text-center px-8">
            <div className="mb-5 flex items-center justify-center w-16 h-16 rounded-full bg-[var(--accent-soft)]">
              <span className="text-[1.75rem] leading-none">📒</span>
            </div>
            <h2 className="mb-1.5" style={{ fontSize: '1.15rem' }}>开始记录你的财务</h2>
            <p className="mb-8 max-w-[340px] text-[0.85rem] leading-relaxed text-[var(--text-secondary)]">
              用自然语言告诉助手你的收支情况，或者查询财务数据
            </p>
            <div className="grid grid-cols-2 gap-2.5 w-full max-w-[400px]">
              {SUGGESTIONS.map(s => (
                <button
                  key={s}
                  onClick={() => onSend(s)}
                  disabled={loading}
                  className="text-left text-[0.82rem] px-4 py-3 rounded-[var(--radius)]
                    bg-[var(--accent-soft)] text-[var(--accent)]
                    border border-transparent
                    hover:border-[var(--border-strong)] hover:shadow-[var(--shadow-sm)]
                    transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed
                    leading-snug"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 消息流 */}
        {messages.length > 0 && (
          <div className="py-5 px-5 space-y-0.5">
            {messages.map(msg => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            {loading && <LoadingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* 输入框 */}
      <div className="mt-3 flex gap-2.5">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入你的收支情况或查询..."
          className="flex-1 px-4 py-2.5 text-[0.85rem] rounded-[var(--radius)] outline-none transition-all
            bg-[var(--bg-card)] border border-[var(--border)]
            focus:border-[var(--accent)] focus:shadow-[var(--shadow)]
            disabled:opacity-50 placeholder:text-[var(--text-muted)]"
          disabled={loading}
        />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={loading || !input.trim()}
          className="px-5 py-2.5 rounded-[var(--radius)] text-[0.85rem] font-medium text-white
            bg-[var(--accent)] transition-all cursor-pointer
            disabled:opacity-40 disabled:cursor-not-allowed
            hover:bg-[var(--accent-hover)] active:scale-[0.98]"
        >
          发送
        </button>
      </div>
    </div>
  )
}

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} py-1.5`}>
      <div
        className={`max-w-[75%] px-4 py-2.5 text-[0.85rem] leading-relaxed
          ${isUser
            ? 'bg-[var(--accent)] text-white rounded-[var(--radius)]'
            : 'bg-[var(--bg)] text-[var(--text-primary)] rounded-[var(--radius)] border border-[var(--border-light)]'
          }`}
      >
        <p className="whitespace-pre-wrap break-words">{msg.content}</p>
        <p className={`text-[0.65rem] mt-1 tabular-nums ${isUser ? 'text-white/60' : 'text-[var(--text-muted)]'}`}>
          {msg.timestamp.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
          {msg.trace_id && (
            <span className="ml-1.5 font-[DM_Mono] opacity-60">{msg.trace_id.slice(0, 8)}</span>
          )}
        </p>
      </div>
    </div>
  )
}

function LoadingIndicator() {
  return (
    <div className="flex justify-start py-1.5">
      <div className="flex items-center gap-1 px-4 py-2.5 rounded-[var(--radius)] border border-[var(--border-light)] bg-[var(--bg)]">
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--text-muted)] animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--text-muted)] animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--text-muted)] animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  )
}
