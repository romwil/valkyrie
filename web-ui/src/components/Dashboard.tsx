import React from 'react'
import { Grid, Paper, Typography, Box, CircularProgress, Card, CardContent } from '@mui/material'
import { TrendingUp, TrendingDown, CheckCircle, Error, Schedule, Work } from '@mui/icons-material'
import { useGetJobStatsQuery, useGetJobsQuery } from '../store/apiSlice'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042']

const Dashboard: React.FC = () => {
  const { data: stats, isLoading: statsLoading } = useGetJobStatsQuery()
  const { data: recentJobs, isLoading: jobsLoading } = useGetJobsQuery()

  if (statsLoading || jobsLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  const statusData = [
    { name: 'Completed', value: stats?.completedJobs || 0, icon: <CheckCircle color="success" /> },
    { name: 'Failed', value: stats?.failedJobs || 0, icon: <Error color="error" /> },
    { name: 'Pending', value: stats?.pendingJobs || 0, icon: <Schedule color="warning" /> },
    { name: 'Running', value: stats?.runningJobs || 0, icon: <Work color="info" /> },
  ]

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      
      <Grid container spacing={3}>
        {/* Status Cards */}
        {statusData.map((item) => (
          <Grid item xs={12} sm={6} md={3} key={item.name}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="textSecondary" gutterBottom>
                      {item.name}
                    </Typography>
                    <Typography variant="h4">
                      {item.value}
                    </Typography>
                  </Box>
                  {item.icon}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}

        {/* Success Rate */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Success Rate
            </Typography>
            <Box display="flex" alignItems="center" gap={2}>
              <Typography variant="h3">
                {stats?.successRate ? `${(stats.successRate * 100).toFixed(1)}%` : '0%'}
              </Typography>
              {stats?.successRate > 0.8 ? (
                <TrendingUp color="success" fontSize="large" />
              ) : (
                <TrendingDown color="error" fontSize="large" />
              )}
            </Box>
          </Paper>
        </Grid>

        {/* Average Processing Time */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Average Processing Time
            </Typography>
            <Typography variant="h3">
              {stats?.averageProcessingTime ? `${stats.averageProcessingTime.toFixed(1)}s` : '0s'}
            </Typography>
          </Paper>
        </Grid>

        {/* Jobs by Day Chart */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Jobs by Day
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={stats?.jobsByDay || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="count" stroke="#8884d8" />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Jobs by Status Pie Chart */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Jobs by Status
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => `${entry.name}: ${entry.value}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {statusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Recent Jobs */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Recent Jobs
            </Typography>
            <Box sx={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '8px' }}>Title</th>
                    <th style={{ textAlign: 'left', padding: '8px' }}>Status</th>
                    <th style={{ textAlign: 'left', padding: '8px' }}>Company</th>
                    <th style={{ textAlign: 'left', padding: '8px' }}>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {recentJobs?.slice(0, 5).map((job) => (
                    <tr key={job.id}>
                      <td style={{ padding: '8px' }}>{job.title}</td>
                      <td style={{ padding: '8px' }}>
                        <Box display="flex" alignItems="center" gap={1}>
                          {job.status === 'completed' && <CheckCircle color="success" fontSize="small" />}
                          {job.status === 'failed' && <Error color="error" fontSize="small" />}
                          {job.status === 'pending' && <Schedule color="warning" fontSize="small" />}
                          {job.status === 'running' && <Work color="info" fontSize="small" />}
                          {job.status}
                        </Box>
                      </td>
                      <td style={{ padding: '8px' }}>{job.companyId}</td>
                      <td style={{ padding: '8px' }}>{new Date(job.createdAt).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}

export default Dashboard
