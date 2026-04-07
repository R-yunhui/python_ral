import { useEffect, useState } from 'react'
import { api } from '../api/client'

interface Budget {
  id: number
  budget_type: string
  category: string | null
  amount: number
  period: string
  created_at: string
}

interface BudgetProgress {
  budget_id: number
  category: string
  budget_amount: number
  spent_amount: number
  remaining: number
  percentage: number
}

/**
 * 预算管理页面
 */
export default function Budgets() {
  const [_budgets, setBudgets] = useState<Budget[]>([])
  const [progress, setProgress] = useState<BudgetProgress[]>([])
  const [form, setForm] = useState({
    budget_type: 'monthly',
    category: '',
    amount: '',
    period: new Date().toISOString().slice(0, 7)
  })

  // 加载预算数据
  const loadBudgets = () => {
    api.getBudgets().then(setBudgets)
    api.getBudgetProgress().then(setProgress)
  }

  useEffect(() => {
    loadBudgets()
  }, [])

  // 提交表单
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.createBudget({
        budget_type: form.budget_type as 'monthly' | 'yearly',
        category: form.category || undefined,
        amount: parseFloat(form.amount),
        period: form.period,
      })
      setForm({
        budget_type: 'monthly',
        category: '',
        amount: '',
        period: new Date().toISOString().slice(0, 7)
      })
      loadBudgets()
      alert('设置成功！')
    } catch (error) {
      console.error('Failed to create budget:', error)
      alert('设置失败，请重试')
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">预算管理</h2>

      {/* 设置预算表单 */}
      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow mb-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">设置预算</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">预算类型</label>
            <select
              value={form.budget_type}
              onChange={(e) => setForm({...form, budget_type: e.target.value})}
              className="w-full rounded-md border border-gray-300 px-3 py-2"
            >
              <option value="monthly">月度预算</option>
              <option value="yearly">年度预算</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">分类（可选）</label>
            <input
              type="text"
              value={form.category}
              onChange={(e) => setForm({...form, category: e.target.value})}
              className="w-full rounded-md border border-gray-300 px-3 py-2"
              placeholder="留空表示总预算"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">预算金额</label>
            <input
              type="number"
              step="0.01"
              value={form.amount}
              onChange={(e) => setForm({...form, amount: e.target.value})}
              className="w-full rounded-md border border-gray-300 px-3 py-2"
              placeholder="0.00"
              required
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700"
            >
              设置预算
            </button>
          </div>
        </div>
      </form>

      {/* 预算执行进度 */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-medium text-gray-900 mb-4">预算执行进度</h3>
        {progress.length === 0 ? (
          <p className="text-gray-500 text-center py-4">暂无预算数据</p>
        ) : (
          <div className="space-y-4">
            {progress.map((p) => (
              <div key={p.budget_id}>
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-medium text-gray-700">{p.category}</span>
                  <span className="text-sm text-gray-600">
                    ¥{p.spent_amount.toFixed(2)} / ¥{p.budget_amount.toFixed(2)}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full ${
                      p.percentage >= 100 ? 'bg-red-600' :
                      p.percentage >= 80 ? 'bg-yellow-600' :
                      'bg-blue-600'
                    }`}
                    style={{ width: `${Math.min(p.percentage, 100)}%` }}
                  />
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  剩余 ¥{p.remaining.toFixed(2)}
                  {p.percentage >= 100 && <span className="text-red-600 ml-2">已超支</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
