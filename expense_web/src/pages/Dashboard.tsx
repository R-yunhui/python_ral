import { useState } from 'react'
import { SummaryCards } from '../components/SummaryCards'
import { ExpenseForm } from '../components/ExpenseForm'
import { ExpenseList } from '../components/ExpenseList'

/**
 * Dashboard 页面
 * 显示概览卡片、快速记账表单和开销列表
 */
export default function Dashboard() {
  const [refreshKey, setRefreshKey] = useState(0)

  // 刷新数据的回调
  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1)
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">概览</h2>

      {/* 概览卡片 */}
      <SummaryCards />

      {/* 快速记账表单 */}
      <ExpenseForm onSuccess={handleRefresh} />

      {/* 开销列表 */}
      <div key={refreshKey}>
        <ExpenseList />
      </div>
    </div>
  )
}
