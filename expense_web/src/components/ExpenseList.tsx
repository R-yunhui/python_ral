import { useEffect, useState } from 'react'
import { api } from '../api/client'

interface Expense {
  id: number
  amount: number
  category: string
  record_date: string
  description: string | null
  created_at: string
}

/**
 * 开销列表组件
 * 显示开销记录列表，支持删除操作
 */
export function ExpenseList() {
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [loading, setLoading] = useState(true)

  // 加载开销列表
  const loadExpenses = () => {
    api.getExpenses().then(data => {
      setExpenses(data)
      setLoading(false)
    }).catch(err => {
      console.error('Failed to fetch expenses:', err)
      setLoading(false)
    })
  }

  useEffect(() => {
    loadExpenses()
  }, [])

  // 删除开销
  const handleDelete = async (id: number) => {
    if (!confirm('确定删除这条开销吗？')) {
      return
    }
    try {
      await api.deleteExpense(id)
      loadExpenses()
      alert('删除成功')
    } catch (error) {
      console.error('Failed to delete expense:', error)
      alert('删除失败，请重试')
    }
  }

  if (loading) {
    return <div className="bg-white rounded-lg shadow p-6">加载中...</div>
  }

  if (expenses.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
        暂无开销记录
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-medium text-gray-900">最近开销</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                日期
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                分类
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                金额
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                描述
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                操作
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {expenses.map((expense) => (
              <tr key={expense.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {expense.record_date}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {expense.category}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600 font-medium">
                  -¥{expense.amount.toFixed(2)}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {expense.description || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <button
                    onClick={() => handleDelete(expense.id)}
                    className="text-red-600 hover:text-red-900 font-medium"
                  >
                    删除
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
