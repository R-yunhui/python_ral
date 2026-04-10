import type { Message } from '../App'

interface SummaryPanelProps {
  messages: Message[]
}

export default function SummaryPanel({ messages }: SummaryPanelProps) {
  const userMessages = messages.filter(m => m.role === 'user')
  const assistantMessages = messages.filter(m => m.role === 'assistant')

  // Simple extraction: count expense-related user messages
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
    <div className="space-y-4">
      {/* Quick stats */}
      <div className="rounded-xl p-5" style={{ background: 'var(--bg-card)', border: '1px solid var(--border-light)', boxShadow: 'var(--shadow)' }}>
        <h3 className="mb-4" style={{ color: 'var(--text-secondary)' }}>对话统计</h3>
        <div className="space-y-3">
          <StatRow label="用户消息" value={userMessages.length.toString()} />
          <StatRow label="助手回复" value={assistantMessages.length.toString()} />
          <StatRow label="支出相关" value={expenseCount.toString()} color="var(--danger)" />
          <StatRow label="收入相关" value={incomeCount.toString()} color="var(--success)" />
          <StatRow label="查询" value={queryCount.toString()} color="var(--warning)" />
        </div>
      </div>

      {/* Usage tips */}
      <div className="rounded-xl p-5" style={{ background: 'var(--accent-light)', border: '1px solid var(--accent)' }}>
        <h3 className="mb-3" style={{ color: 'var(--accent)' }}>使用提示</h3>
        <ul className="space-y-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
          <li className="flex gap-2">
            <span>📝</span>
            <span>记账：「午餐30元」「打车花了45」</span>
          </li>
          <li className="flex gap-2">
            <span>📊</span>
            <span>查询：「这个月花了多少」「看看餐饮预算」</span>
          </li>
          <li className="flex gap-2">
            <span>🔀</span>
            <span>混合：「午饭30块，帮我看这个月餐饮总额」</span>
          </li>
        </ul>
      </div>

      {/* Trace ID */}
      {lastTrace && (
        <div className="rounded-xl p-4 text-xs" style={{ background: 'var(--bg-card)', border: '1px solid var(--border-light)' }}>
          <span style={{ color: 'var(--text-muted)' }}>最近请求 trace_id</span>
          <p className="font-mono mt-1 break-all" style={{ color: 'var(--text-secondary)' }}>
            {lastTrace}
          </p>
        </div>
      )}
    </div>
  )
}

function StatRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex justify-between items-center">
      <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
      <span className="font-semibold text-lg" style={{ color: color ?? 'var(--text-primary)' }}>
        {value}
      </span>
    </div>
  )
}
