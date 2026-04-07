import { useEffect, useState } from 'react'
import {
  PieChart, Pie, Cell,
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { api } from '../api/client'

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#0088fe', '#00C49F', '#FFBB28', '#FF8042']

/**
 * 分类占比饼图
 */
function CategoryPieChart() {
  const [data, setData] = useState<{ name: string; value: number }[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getSummary().then(summary => {
      const chartData = Object.entries(summary.category_breakdown)
        .map(([name, value]) => ({ name, value: value as number }))
      setData(chartData)
      setLoading(false)
    }).catch(() => {
      setLoading(false)
    })
  }, [])

  if (loading) return <div className="h-64 flex items-center justify-center text-gray-500">加载中...</div>
  if (data.length === 0) return <div className="h-64 flex items-center justify-center text-gray-500">暂无数据</div>

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ name, value }) => `${name}: ¥${value}`}
          outerRadius={80}
          fill="#8884d8"
          dataKey="value"
        >
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip formatter={(value: number) => `¥${value.toFixed(2)}`} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}

/**
 * 收支趋势柱状图
 */
function TrendBarChart() {
  const [data, setData] = useState<{ period: string; income: number; expense: number }[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getTrend(6).then(data => {
      setData(data.map((d: any) => ({
        ...d,
        period: d.period.slice(5) // 只显示 MM
      })))
      setLoading(false)
    }).catch(() => {
      setLoading(false)
    })
  }, [])

  if (loading) return <div className="h-64 flex items-center justify-center text-gray-500">加载中...</div>
  if (data.length === 0) return <div className="h-64 flex items-center justify-center text-gray-500">暂无数据</div>

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <XAxis dataKey="period" />
        <YAxis />
        <Tooltip formatter={(value: number) => `¥${value.toFixed(2)}`} />
        <Legend />
        <Bar dataKey="income" fill="#82ca9d" name="收入" />
        <Bar dataKey="expense" fill="#ff8042" name="支出" />
      </BarChart>
    </ResponsiveContainer>
  )
}

/**
 * 统计页面
 */
export default function Statistics() {
  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-6">统计</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 分类占比 */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">分类占比</h3>
          <CategoryPieChart />
        </div>

        {/* 收支趋势 */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-medium text-gray-900 mb-4">收支趋势</h3>
          <TrendBarChart />
        </div>
      </div>
    </div>
  )
}
