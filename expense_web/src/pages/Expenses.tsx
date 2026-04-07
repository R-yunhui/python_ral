import { useState } from 'react'
import { ExpenseForm } from '../components/ExpenseForm'
import { ExpenseList } from '../components/ExpenseList'

/**
 * 开销管理页面
 */
export default function Expenses() {
  const [refreshKey, setRefreshKey] = useState(0)

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1)
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">开销管理</h2>
      <ExpenseForm onSuccess={handleRefresh} />
      <div key={refreshKey}>
        <ExpenseList />
      </div>
    </div>
  )
}
