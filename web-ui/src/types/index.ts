export interface Job {
  id: string
  title: string
  description: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  companyId: string
  createdAt: string
  updatedAt: string
  progress: number
  result?: any
  error?: string
  fileUrl?: string
  priority: 'low' | 'medium' | 'high'
}

export interface Company {
  id: string
  name: string
  domain: string
  mdmEnabled: boolean
  apiKey?: string
  createdAt: string
  updatedAt: string
  jobCount?: number
  settings?: {
    autoRetry: boolean
    maxRetries: number
    webhookUrl?: string
  }
}

export interface Analytics {
  totalJobs: number
  completedJobs: number
  failedJobs: number
  pendingJobs: number
  averageProcessingTime: number
  jobsByStatus: {
    status: string
    count: number
  }[]
  jobsByCompany: {
    company: string
    count: number
  }[]
  jobsByDay: {
    date: string
    count: number
  }[]
  successRate: number
}

export interface WebSocketMessage {
  type: 'job_update' | 'job_created' | 'job_completed' | 'analytics_update'
  payload: any
}
