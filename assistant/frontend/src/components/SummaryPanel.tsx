import type { Message } from '../App'

interface SummaryPanelProps {
  messages: Message[]
}

export default function SummaryPanel({ messages }: SummaryPanelProps) {
  const userMessages = messages.filter(m => m.role === 'user')
  const assistantMessages = messages.filter(m => m.role === 'assistant')

  const expenseKeywords = ['花', '买', '支', '付', '费', '元', '块', '餐', '饭', '吃', '打车', '地铁', '公交', '加油', '房租', '水电']
  const incomeKeywords = ['工资', '收入', '奖金', '报销', '收到', '入账', '到账', '理财', '利息']

  const expenseCount = userMessages.filter(m =>
    expenseKeywords.some(k => m.content.includes(k))
  ).length

  const incomeCount = userMessages.filter(m =>
    incomeKeywords.some(k => m.content.includes(k))
  ).length

  const queryCount = userMessages.filter(m =>
    ['看', '查', '多少', '预算', '超', '统计', '汇总', '趋势'].some(k => m.content.includes(k))
  ).length

  const lastTrace = assistantMessages.at(-1)?.trace_id

  return (
    <div className="sticky top-0 space-y-3">
      {/* 统计卡片 */}
      <div className="rounded-[var(--radius-lg)] bg-[var(--bg-card)] border border-[var(--border-light)] shadow-[var(--shadow)] p-5">
        <h3 className="mb-3.5 text-[0.75rem] font-normal text-[var(--text-muted)] tracking-[0.06em] uppercase">
          对话统计
        </h3>
        <div className="space-y-3">
          <StatRow label="用户消息" value={userMessages.length} />
          <StatRow label="助手回复" value={assistantMessages.length} />
          <StatRow label="支出相关" value={expenseCount} />
          <StatRow label="收入相关" value={incomeCount} />
          <StatRow label="查询请求" value={queryCount} />
        </div>
      </div>

      {/* 使用提示 */}
      <div className="rounded-[var(--radius-lg)] p-5 border border-[var(--border)] bg-[var(--accent-soft)]">
        <h3 className="mb-2.5 text-[0.75rem] font-normal text-[var(--accent)] tracking-[0.06em]">
          使用方式
        </h3>
        <ul className="space-y-2 text-[0.78rem] leading-relaxed text-[var(--text-secondary)]">
          <li className="flex gap-2 items-start">
            <span className="text-[0.6rem] mt-1.5 text-[var(--accent)]">▸</span>
            <span>「午餐30元」「打车花了45」</span>
          </li>
          <li className="flex gap-2 items-start">
            <span className="text-[0.6rem] mt-1.5 text-[var(--accent)]">▸</span>
            <span>「这个月花了多少」「看看餐饮预算」</span>
          </li>
          <li className="flex gap-2 items-start">
            <span className="text-[0.6rem] mt-1.5 text-[var(--accent)]">▸</span>
            <span>「午饭30块，帮我看这个月餐饮总额」</span>
          </li>
        </ul>
      </div>

      {/* Trace ID */}
      {lastTrace && (
        <div className="rounded-[var(--radius)] p-3 border border-[var(--border-light)] bg-[var(--bg-card)]">
          <span className="text-[0.65rem] text-[var(--text-muted)]">trace_id</span>
          <p className="font-[DM_Mono] text-[0.6rem] mt-0.5 break-all text-[var(--text-secondary)]">
            {lastTrace}
          </p>
        </div>
      )}
    </div>
  )
}

function StatRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex justify-between items-baseline">
      <span className="text-[0.78rem] text-[var(--text-secondary)]">{label}</span>
      <span className="font-[DM_Mono] text-[0.95rem] tabular-nums" style={{ color: 'var(--text-primary)' }}>
        {value}
      </span>
    </div>
  )
}
