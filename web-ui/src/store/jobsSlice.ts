import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { Job } from '../types'

interface JobsState {
  selectedJob: Job | null
  filter: {
    status?: string
    companyId?: string
    priority?: string
  }
  sortBy: 'createdAt' | 'updatedAt' | 'priority' | 'status'
  sortOrder: 'asc' | 'desc'
}

const initialState: JobsState = {
  selectedJob: null,
  filter: {},
  sortBy: 'createdAt',
  sortOrder: 'desc',
}

const jobsSlice = createSlice({
  name: 'jobs',
  initialState,
  reducers: {
    setSelectedJob: (state, action: PayloadAction<Job | null>) => {
      state.selectedJob = action.payload
    },
    setFilter: (state, action: PayloadAction<JobsState['filter']>) => {
      state.filter = action.payload
    },
    setSorting: (state, action: PayloadAction<{ sortBy: JobsState['sortBy']; sortOrder: JobsState['sortOrder'] }>) => {
      state.sortBy = action.payload.sortBy
      state.sortOrder = action.payload.sortOrder
    },
    updateJobProgress: (state, action: PayloadAction<{ id: string; progress: number }>) => {
      if (state.selectedJob?.id === action.payload.id) {
        state.selectedJob.progress = action.payload.progress
      }
    },
  },
})

export const { setSelectedJob, setFilter, setSorting, updateJobProgress } = jobsSlice.actions
export default jobsSlice.reducer
