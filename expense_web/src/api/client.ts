import axios from 'axios'

const API_BASE = '/api'

// API 客户端封装
export const api = {
  // 开销相关接口
  getExpenses: async (params?: { category?: string; start_date?: string; end_date?: string }) => {
    const response = await axios.get(`${API_BASE}/expenses`, { params })
    return response.data
  },

  createExpense: async (data: { amount: number; category: string; record_date: string; description?: string; tags?: string[] }) => {
    const response = await axios.post(`${API_BASE}/expenses`, data)
    return response.data
  },

  deleteExpense: async (id: number) => {
    const response = await axios.delete(`${API_BASE}/expenses/${id}`)
    return response.data
  },

  // 收入相关接口
  getIncomes: async () => {
    const response = await axios.get(`${API_BASE}/incomes`)
    return response.data
  },

  createIncome: async (data: { amount: number; source: string; record_date: string; note?: string }) => {
    const response = await axios.post(`${API_BASE}/incomes`, data)
    return response.data
  },

  // 预算相关接口
  getBudgets: async (params?: { budget_type?: string; period?: string }) => {
    const response = await axios.get(`${API_BASE}/budgets`, { params })
    return response.data
  },

  createBudget: async (data: { budget_type: string; category?: string; amount: number; period: string }) => {
    const response = await axios.post(`${API_BASE}/budgets`, data)
    return response.data
  },

  // 统计相关接口
  getSummary: async (year?: number, month?: number) => {
    const params: Record<string, any> = {}
    if (year) params.year = year
    if (month) params.month = month
    const response = await axios.get(`${API_BASE}/stats/summary`, { params })
    return response.data
  },

  getBudgetProgress: async (year?: number, month?: number) => {
    const params: Record<string, any> = {}
    if (year) params.year = year
    if (month) params.month = month
    const response = await axios.get(`${API_BASE}/stats/budget-progress`, { params })
    return response.data
  },

  getTrend: async (months: number = 6) => {
    const response = await axios.get(`${API_BASE}/stats/trend`, { params: { months } })
    return response.data
  },

  // Agent 查询接口
  queryAgent: async (query: string) => {
    const response = await axios.post(`${API_BASE}/agent/query`, { query })
    return response.data
  },
}
