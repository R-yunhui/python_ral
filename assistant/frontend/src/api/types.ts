export interface ChatRequest {
  user_id: string
  message: string
}

export interface ChatResponse {
  answer: string
  trace_id: string
  lang: string
}

export interface HealthResponse {
  status: string
}
