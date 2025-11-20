import React, { useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Stack,
  Chip,
} from '@mui/material'
import { CloudUpload, Send } from '@mui/icons-material'
import { useCreateJobMutation } from '../store/apiSlice'
import { useGetCompaniesQuery } from '../store/apiSlice'

const JobCreation: React.FC = () => {
  const [createJob, { isLoading, isSuccess, isError, error }] = useCreateJobMutation()
  const { data: companies } = useGetCompaniesQuery()
  
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    companyId: '',
    priority: 'medium' as 'low' | 'medium' | 'high',
    file: null as File | null,
  })

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSelectChange = (name: string) => (e: any) => {
    setFormData(prev => ({ ...prev, [name]: e.target.value }))
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFormData(prev => ({ ...prev, file: e.target.files![0] }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const jobData = new FormData()
    jobData.append('title', formData.title)
    jobData.append('description', formData.description)
    jobData.append('companyId', formData.companyId)
    jobData.append('priority', formData.priority)
    if (formData.file) {
      jobData.append('file', formData.file)
    }

    try {
      await createJob({
        title: formData.title,
        description: formData.description,
        companyId: formData.companyId,
        priority: formData.priority,
        status: 'pending',
      }).unwrap()
      
      // Reset form on success
      setFormData({
        title: '',
        description: '',
        companyId: '',
        priority: 'medium',
        file: null,
      })
    } catch (err) {
      console.error('Failed to create job:', err)
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Create New Job
      </Typography>

      <Paper sx={{ p: 3, maxWidth: 800 }}>
        <form onSubmit={handleSubmit}>
          <Stack spacing={3}>
            {isSuccess && (
              <Alert severity="success">
                Job created successfully!
              </Alert>
            )}
            
            {isError && (
              <Alert severity="error">
                Failed to create job. Please try again.
              </Alert>
            )}

            <TextField
              fullWidth
              label="Job Title"
              name="title"
              value={formData.title}
              onChange={handleInputChange}
              required
              variant="outlined"
            />

            <TextField
              fullWidth
              label="Description"
              name="description"
              value={formData.description}
              onChange={handleInputChange}
              required
              multiline
              rows={4}
              variant="outlined"
            />

            <FormControl fullWidth required>
              <InputLabel>Company</InputLabel>
              <Select
                value={formData.companyId}
                onChange={handleSelectChange('companyId')}
                label="Company"
              >
                {companies?.map((company) => (
                  <MenuItem key={company.id} value={company.id}>
                    {company.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth required>
              <InputLabel>Priority</InputLabel>
              <Select
                value={formData.priority}
                onChange={handleSelectChange('priority')}
                label="Priority"
              >
                <MenuItem value="low">Low</MenuItem>
                <MenuItem value="medium">Medium</MenuItem>
                <MenuItem value="high">High</MenuItem>
              </Select>
            </FormControl>

            <Box>
              <input
                accept="*/*"
                style={{ display: 'none' }}
                id="file-upload"
                type="file"
                onChange={handleFileChange}
              />
              <label htmlFor="file-upload">
                <Button
                  variant="outlined"
                  component="span"
                  startIcon={<CloudUpload />}
                  fullWidth
                >
                  Upload File
                </Button>
              </label>
              {formData.file && (
                <Box mt={1}>
                  <Chip
                    label={formData.file.name}
                    onDelete={() => setFormData(prev => ({ ...prev, file: null }))}
                    color="primary"
                    variant="outlined"
                  />
                </Box>
              )}
            </Box>

            <Button
              type="submit"
              variant="contained"
              size="large"
              startIcon={isLoading ? <CircularProgress size={20} /> : <Send />}
              disabled={isLoading}
              fullWidth
            >
              {isLoading ? 'Creating...' : 'Create Job'}
            </Button>
          </Stack>
        </form>
      </Paper>
    </Box>
  )
}

export default JobCreation
