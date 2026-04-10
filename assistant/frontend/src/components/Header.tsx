interface HeaderProps {
  messageCount: number
  onClear: () => void
}

export default function Header({ messageCount, onClear }: HeaderProps) {
  return (
    <header className="border-b bg-white" style={{ borderColor: 'var(--border)' }}>
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="text-2xl">📒</div>
          <div>
            <h1 style={{ fontSize: '1.125rem' }}>个人财务助手</h1>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              自然语言记账，智能管理预算
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {messageCount > 0 && (
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
              {messageCount} 条对话
            </span>
          )}
          {messageCount > 0 && (
            <button
              onClick={onClear}
              className="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors cursor-pointer"
              style={{
                color: 'var(--text-secondary)',
                background: 'transparent',
                border: '1px solid var(--border)',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'var(--border-light)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'transparent'
              }}
            >
              清空对话
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
