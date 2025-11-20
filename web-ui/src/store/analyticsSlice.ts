import { createSlice, PayloadAction } from '@reduxjs/toolkit'

interface AnalyticsState {
  dateRange: {
    start: string
    end: string
  }
  selectedMetric: 'jobs' | 'success_rate' | 'processing_time' | 'companies'
}

const initialState: AnalyticsState = {
  dateRange: {
    start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  },
  selectedMetric: 'jobs',
}

const analyticsSlice = createSlice({
  name: 'analytics',
  initialState,
  reducers: {
    setDateRange: (state, action: PayloadAction<{ start: string; end: string }>) => {
      state.dateRange = action.payload
    },
    setSelectedMetric: (state, action: PayloadAction<AnalyticsState['selectedMetric']>) => {
      state.selectedMetric = action.payload
    },
  },
})

export const { setDateRange, setSelectedMetric } = analyticsSlice.actions
export default analyticsSlice.reducer
