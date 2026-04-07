import { useEffect, useState } from 'react'
import { api } from '../api/client'

/**
 * 概览卡片组件
 * 显示本月收入、支出、结余
 */
export function SummaryCards() {
  const [summary, setSummary] = useState<{
    total_income: number
    total_expense: number
    balance: number
  } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getSummary().then(data => {
      setSummary(data)
      setLoading(false)
    }).catch(err => {
      console.error('Failed to fetch summary:', err)
      setLoading(false)
    })
  }, [])

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-6 rounded-lg shadow">加载中...</div>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {/* 本月收入 */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-sm font-medium text-gray-500">本月收入</h3>
        <p className="text-2xl font-semibold text-green-600 mt-2">
          ¥{summary?.total_income.toFixed(2)}
        </p>
      </div>
      {/* 本月支出 */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-sm font-medium text-gray-500">本月支出</h3>
        <p className="text-2xl font-semibold text-red-600 mt-2">
          ¥{summary?.total_expense.toFixed(2)}
        </p>
      </div>
      {/* 本月结余 */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-sm font-medium text-gray-500">本月结余</h3>
        <p className={`text-2xl font-semibold mt-2 ${
          (summary?.balance || 0) >= 0 ? 'text-green-600' : 'text-red-600'
        }`}>
          ¥{summary?.balance.toFixed(2)}
        </p>
      </div>
    </div>
  )
}
