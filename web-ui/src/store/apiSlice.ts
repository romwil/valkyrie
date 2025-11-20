import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'
import { Job, Company, Analytics } from '../types'

export const apiSlice = createApi({
  reducerPath: 'api',
  baseQuery: fetchBaseQuery({ 
    baseUrl: '/api',
    prepareHeaders: (headers) => {
      // Add auth token if available
      const token = localStorage.getItem('authToken')
      if (token) {
        headers.set('authorization', `Bearer ${token}`)
      }
      return headers
    },
  }),
  tagTypes: ['Job', 'Company', 'Analytics'],
  endpoints: (builder) => ({
    // Jobs endpoints
    getJobs: builder.query<Job[], void>({
      query: () => '/jobs',
      providesTags: ['Job'],
    }),
    getJob: builder.query<Job, string>({
      query: (id) => `/jobs/${id}`,
      providesTags: ['Job'],
    }),
    createJob: builder.mutation<Job, Partial<Job>>({
      query: (job) => ({
        url: '/jobs',
        method: 'POST',
        body: job,
      }),
      invalidatesTags: ['Job', 'Analytics'],
    }),
    updateJob: builder.mutation<Job, { id: string; updates: Partial<Job> }>({
      query: ({ id, updates }) => ({
        url: `/jobs/${id}`,
        method: 'PUT',
        body: updates,
      }),
      invalidatesTags: ['Job', 'Analytics'],
    }),
    
    // Companies endpoints
    getCompanies: builder.query<Company[], void>({
      query: () => '/companies',
      providesTags: ['Company'],
    }),
    createCompany: builder.mutation<Company, Partial<Company>>({
      query: (company) => ({
        url: '/companies',
        method: 'POST',
        body: company,
      }),
      invalidatesTags: ['Company'],
    }),
    
    // Analytics endpoints
    getAnalytics: builder.query<Analytics, void>({
      query: () => '/analytics',
      providesTags: ['Analytics'],
    }),
    getJobStats: builder.query<any, void>({
      query: () => '/analytics/job-stats',
      providesTags: ['Analytics'],
    }),
  }),
})

export const {
  useGetJobsQuery,
  useGetJobQuery,
  useCreateJobMutation,
  useUpdateJobMutation,
  useGetCompaniesQuery,
  useCreateCompanyMutation,
  useGetAnalyticsQuery,
  useGetJobStatsQuery,
} = apiSlice
