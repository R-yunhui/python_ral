import { useState } from 'react'
import { api } from '../api/client'

const CATEGORIES = ['餐饮', '交通', '购物', '娱乐', '居住', '医疗', '其他']

interface ExpenseFormProps {
  onSuccess: () => void
}

/**
 * 开销表单组件
 * 用于快速添加开销记录
 */
export function ExpenseForm({ onSuccess }: ExpenseFormProps) {
  const [amount, setAmount] = useState('')
  const [category, setCategory] = useState('餐饮')
  const [recordDate, setRecordDate] = useState(new Date().toISOString().split('T')[0])
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)

    try {
      await api.createExpense({
        amount: parseFloat(amount),
        category,
        record_date: recordDate,
        description: description || undefined,
      })
      // 清空表单
      setAmount('')
      setDescription('')
      // 通知父组件刷新数据
      onSuccess()
      alert('添加成功！')
    } catch (error) {
      console.error('Failed to create expense:', error)
      alert('添加失败，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow mb-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">快速记账</h3>
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {/* 金额 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">金额</label>
          <input
            type="number"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            placeholder="0.00"
            required
          />
        </div>
        {/* 分类 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">分类</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          >
            {CATEGORIES.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>
        {/* 日期 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">日期</label>
          <input
            type="date"
            value={recordDate}
            onChange={(e) => setRecordDate(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
          />
        </div>
        {/* 描述 */}
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            placeholder="可选，如：午餐、打车等"
          />
        </div>
      </div>
      {/* 提交按钮 */}
      <div className="mt-4">
        <button
          type="submit"
          disabled={submitting}
          className="w-full md:w-auto bg-indigo-600 text-white px-6 py-2 rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting ? '添加中...' : '添加开销'}
        </button>
      </div>
    </form>
  )
}
