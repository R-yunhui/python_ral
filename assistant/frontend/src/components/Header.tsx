interface HeaderProps {
  messageCount: number
  onClear: () => void
}

export default function Header({ messageCount, onClear }: HeaderProps) {
  return (
    <header className="relative z-10 bg-[var(--bg-card)] border-b border-[var(--border)]">
      <div className="max-w-[1200px] mx-auto px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-[1.25rem] leading-none opacity-80">📒</span>
          <div className="leading-tight">
            <h1 className="text-[0.95rem] tracking-[0.02em]">财务助手</h1>
          </div>
        </div>
        {messageCount > 0 && (
          <div className="flex items-center gap-3">
            <span className="text-[0.75rem] text-[var(--text-muted)] tabular-nums">
              {messageCount} 条
            </span>
            <button
              onClick={onClear}
              className="text-[0.75rem] text-[var(--text-secondary)] px-3 py-1 rounded-md border border-[var(--border)] bg-transparent cursor-pointer
                         hover:bg-[var(--bg)] transition-colors"
            >
              清空
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
