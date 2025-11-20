import React from 'react'
import {
  Box,
  Paper,
  Typography,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Card,
  CardContent,
  Chip,
  Stack,
} from '@mui/material'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts'
import { TrendingUp, TrendingDown, Speed, Business } from '@mui/icons-material'
import { useGetAnalyticsQuery } from '../store/apiSlice'
import { useAppDispatch, useAppSelector } from '../hooks/redux'
import { setDateRange, setSelectedMetric } from '../store/analyticsSlice'

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8']

const Analytics: React.FC = () => {
  const dispatch = useAppDispatch()
  const { dateRange, selectedMetric } = useAppSelector(state => state.analytics)
  const { data: analytics, isLoading } = useGetAnalyticsQuery()

  const performanceData = [
    { metric: 'Success Rate', value: (analytics?.successRate || 0) * 100, fullMark: 100 },
    { metric: 'Avg Speed', value: analytics?.averageProcessingTime ? (100 - Math.min(analytics.averageProcessingTime, 100)) : 0, fullMark: 100 },
    { metric: 'Completion', value: analytics?.completedJobs ? (analytics.completedJobs / (analytics.totalJobs || 1)) * 100 : 0, fullMark: 100 },
    { metric: 'Efficiency', value: 85, fullMark: 100 },
  ]

  const metricCards = [
    {
      title: 'Total Jobs',
      value: analytics?.totalJobs || 0,
      change: '+12%',
      trend: 'up',
      icon: <Work />,
    },
    {
      title: 'Success Rate',
      value: `${((analytics?.successRate || 0) * 100).toFixed(1)}%`,
      change: analytics?.successRate > 0.8 ? '+5%' : '-3%',
      trend: analytics?.successRate > 0.8 ? 'up' : 'down',
      icon: <TrendingUp />,
    },
    {
      title: 'Avg Processing',
      value: `${analytics?.averageProcessingTime?.toFixed(1) || 0}s`,
      change: '-8%',
      trend: 'up',
      icon: <Speed />,
    },
    {
      title: 'Active Companies',
      value: analytics?.jobsByCompany?.length || 0,
      change: '+2',
      trend: 'up',
      icon: <Business />,
    },
  ]

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          Analytics Dashboard
        </Typography>
        <Stack direction="row" spacing={2}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Date Range</InputLabel>
            <Select
              value={dateRange.start}
              onChange={(e) => dispatch(setDateRange({ start: e.target.value, end: dateRange.end }))}
              label="Date Range"
            >
              <MenuItem value={new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]}>Last 7 days</MenuItem>
              <MenuItem value={new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]}>Last 30 days</MenuItem>
              <MenuItem value={new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]}>Last 90 days</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Metric</InputLabel>
            <Select
              value={selectedMetric}
              onChange={(e) => dispatch(setSelectedMetric(e.target.value as any))}
              label="Metric"
            >
              <MenuItem value="jobs">Jobs</MenuItem>
              <MenuItem value="success_rate">Success Rate</MenuItem>
              <MenuItem value="processing_time">Processing Time</MenuItem>
              <MenuItem value="companies">Companies</MenuItem>
            </Select>
          </FormControl>
        </Stack>
      </Box>

      {/* Metric Cards */}
      <Grid container spacing={3} mb={3}>
        {metricCards.map((card) => (
          <Grid item xs={12} sm={6} md={3} key={card.title}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                  <Box>
                    <Typography color="textSecondary" gutterBottom variant="body2">
                      {card.title}
                    </Typography>
                    <Typography variant="h4">
                      {card.value}
                    </Typography>
                    <Box display="flex" alignItems="center" mt={1}>
                      {card.trend === 'up' ? (
                        <TrendingUp color="success" fontSize="small" />
                      ) : (
                        <TrendingDown color="error" fontSize="small" />
                      )}
                      <Typography
                        variant="body2"
                        color={card.trend === 'up' ? 'success.main' : 'error.main'}
                        ml={0.5}
                      >
                        {card.change}
                      </Typography>
                    </Box>
                  </Box>
                  <Box sx={{ color: 'primary.main' }}>
                    {card.icon}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3}>
        {/* Jobs Trend Chart */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Jobs Trend Over Time
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={analytics?.jobsByDay || []}>
                <defs>
                  <linearGradient id="colorJobs" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#8884d8" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="count" stroke="#8884d8" fillOpacity={1} fill="url(#colorJobs)" />
              </AreaChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Performance Radar */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Performance Metrics
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <RadarChart data={performanceData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="metric" />
                <PolarRadiusAxis angle={90} domain={[0, 100]} />
                <Radar name="Performance" dataKey="value" stroke="#8884d8" fill="#8884d8" fillOpacity={0.6} />
              </RadarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Jobs by Status */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Jobs by Status Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={analytics?.jobsByStatus || []}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => `${entry.status}: ${entry.count}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="count"
                >
                  {(analytics?.jobsByStatus || []).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Jobs by Company */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Jobs by Company
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={analytics?.jobsByCompany?.slice(0, 5) || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="company" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#8884d8">
                  {(analytics?.jobsByCompany?.slice(0, 5) || []).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Processing Time Distribution */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Processing Time Analysis
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={analytics?.jobsByDay || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Legend />
                <Line yAxisId="left" type="monotone" dataKey="count" stroke="#8884d8" name="Job Count" />
                <Line yAxisId="right" type="monotone" dataKey="avgTime" stroke="#82ca9d" name="Avg Time (s)" />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}

export default Analytics
