import React, { useEffect, useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  LinearProgress,
  IconButton,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Stack,
  Tooltip,
  Button,
} from '@mui/material'
import { Refresh, Visibility, Stop, PlayArrow } from '@mui/icons-material'
import { useGetJobsQuery, useUpdateJobMutation } from '../store/apiSlice'
import { useAppDispatch, useAppSelector } from '../hooks/redux'
import { setFilter, setSorting, updateJobProgress } from '../store/jobsSlice'
import { io, Socket } from 'socket.io-client'

const JobMonitoring: React.FC = () => {
  const dispatch = useAppDispatch()
  const { filter, sortBy, sortOrder } = useAppSelector(state => state.jobs)
  const { data: jobs, isLoading, refetch } = useGetJobsQuery()
  const [updateJob] = useUpdateJobMutation()
  const [socket, setSocket] = useState<Socket | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    // Connect to WebSocket for real-time updates
    const newSocket = io('ws://localhost:8000', {
      path: '/ws',
      transports: ['websocket'],
    })

    newSocket.on('job_update', (data) => {
      dispatch(updateJobProgress({ id: data.jobId, progress: data.progress }))
      refetch()
    })

    setSocket(newSocket)

    return () => {
      newSocket.close()
    }
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success'
      case 'failed': return 'error'
      case 'running': return 'info'
      case 'pending': return 'warning'
      default: return 'default'
    }
  }

  const handleStatusChange = async (jobId: string, newStatus: string) => {
    try {
      await updateJob({ id: jobId, updates: { status: newStatus as any } })
      refetch()
    } catch (error) {
      console.error('Failed to update job status:', error)
    }
  }

  const filteredJobs = jobs?.filter(job => {
    const matchesSearch = job.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         job.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = !filter.status || job.status === filter.status
    const matchesPriority = !filter.priority || job.priority === filter.priority
    const matchesCompany = !filter.companyId || job.companyId === filter.companyId
    
    return matchesSearch && matchesStatus && matchesPriority && matchesCompany
  })

  const sortedJobs = [...(filteredJobs || [])].sort((a, b) => {
    let aValue = a[sortBy]
    let bValue = b[sortBy]
    
    if (sortBy === 'createdAt' || sortBy === 'updatedAt') {
      aValue = new Date(aValue).getTime()
      bValue = new Date(bValue).getTime()
    }
    
    if (sortOrder === 'asc') {
      return aValue > bValue ? 1 : -1
    } else {
      return aValue < bValue ? 1 : -1
    }
  })

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          Job Monitoring
        </Typography>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={() => refetch()}
        >
          Refresh
        </Button>
      </Box>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Stack direction="row" spacing={2}>
          <TextField
            label="Search"
            variant="outlined"
            size="small"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            sx={{ flexGrow: 1 }}
          />
          
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={filter.status || ''}
              onChange={(e) => dispatch(setFilter({ ...filter, status: e.target.value }))}
              label="Status"
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="pending">Pending</MenuItem>
              <MenuItem value="running">Running</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
              <MenuItem value="failed">Failed</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Priority</InputLabel>
            <Select
              value={filter.priority || ''}
              onChange={(e) => dispatch(setFilter({ ...filter, priority: e.target.value }))}
              label="Priority"
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="low">Low</MenuItem>
              <MenuItem value="medium">Medium</MenuItem>
              <MenuItem value="high">High</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Sort By</InputLabel>
            <Select
              value={sortBy}
              onChange={(e) => dispatch(setSorting({ sortBy: e.target.value as any, sortOrder }))}
              label="Sort By"
            >
              <MenuItem value="createdAt">Created</MenuItem>
              <MenuItem value="updatedAt">Updated</MenuItem>
              <MenuItem value="priority">Priority</MenuItem>
              <MenuItem value="status">Status</MenuItem>
            </Select>
          </FormControl>
        </Stack>
      </Paper>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Title</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Priority</TableCell>
              <TableCell>Progress</TableCell>
              <TableCell>Company</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <LinearProgress />
                </TableCell>
              </TableRow>
            ) : sortedJobs?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  No jobs found
                </TableCell>
              </TableRow>
            ) : (
              sortedJobs?.map((job) => (
                <TableRow key={job.id}>
                  <TableCell>{job.title}</TableCell>
                  <TableCell>
                    <Chip
                      label={job.status}
                      color={getStatusColor(job.status)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={job.priority}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      <LinearProgress
                        variant="determinate"
                        value={job.progress}
                        sx={{ flexGrow: 1, minWidth: 100 }}
                      />
                      <Typography variant="body2">{job.progress}%</Typography>
                    </Box>
                  </TableCell>
                  <TableCell>{job.companyId}</TableCell>
                  <TableCell>{new Date(job.createdAt).toLocaleString()}</TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1}>
                      <Tooltip title="View Details">
                        <IconButton size="small">
                          <Visibility fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      {job.status === 'running' && (
                        <Tooltip title="Stop Job">
                          <IconButton
                            size="small"
                            onClick={() => handleStatusChange(job.id, 'failed')}
                          >
                            <Stop fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {job.status === 'pending' && (
                        <Tooltip title="Start Job">
                          <IconButton
                            size="small"
                            onClick={() => handleStatusChange(job.id, 'running')}
                          >
                            <PlayArrow fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

export default JobMonitoring
