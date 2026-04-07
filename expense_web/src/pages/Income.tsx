import { useEffect, useState } from 'react'
import { api } from '../api/client'

interface Income {
  id: number
  amount: number
  source: string
  record_date: string
  note: string | null
  created_at: string
}

/**
 * 收入管理页面
 */
export default function Income() {
  const [incomes, setIncomes] = useState<Income[]>([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({
    amount: '',
    source: '',
    record_date: new Date().toISOString().split('T')[0],
    note: ''
  })

  // 加载收入列表
  const loadIncomes = () => {
    api.getIncomes().then(data => {
      setIncomes(data)
      setLoading(false)
    })
  }

  useEffect(() => {
    loadIncomes()
  }, [])

  // 提交表单
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await api.createIncome({
        amount: parseFloat(form.amount),
        source: form.source,
        record_date: form.record_date,
        note: form.note || undefined,
      })
      // 清空表单
      setForm({
        amount: '',
        source: '',
        record_date: new Date().toISOString().split('T')[0],
        note: ''
      })
      loadIncomes()
      alert('添加成功！')
    } catch (error) {
      console.error('Failed to create income:', error)
      alert('添加失败，请重试')
    }
  }

  if (loading) {
    return <div className="bg-white rounded-lg shadow p-6">加载中...</div>
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">收入管理</h2>

      {/* 添加收入表单 */}
      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">金额</label>
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
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">来源</label>
            <input
              type="text"
              value={form.source}
              onChange={(e) => setForm({...form, source: e.target.value})}
              className="w-full rounded-md border border-gray-300 px-3 py-2"
              placeholder="如：工资、奖金、兼职等"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">日期</label>
            <input
              type="date"
              value={form.record_date}
              onChange={(e) => setForm({...form, record_date: e.target.value})}
              className="w-full rounded-md border border-gray-300 px-3 py-2"
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700"
            >
              添加收入
            </button>
          </div>
        </div>
        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">备注</label>
          <input
            type="text"
            value={form.note}
            onChange={(e) => setForm({...form, note: e.target.value})}
            className="w-full rounded-md border border-gray-300 px-3 py-2"
            placeholder="可选"
          />
        </div>
      </form>

      {/* 收入列表 */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">收入记录</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">日期</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">来源</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">金额</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">备注</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {incomes.map((income) => (
                <tr key={income.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{income.record_date}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{income.source}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600 font-medium">+¥{income.amount.toFixed(2)}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{income.note || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
