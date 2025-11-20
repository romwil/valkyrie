import React, { useState } from 'react'
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
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Switch,
  FormControlLabel,
  IconButton,
  Chip,
  Stack,
  Alert,
} from '@mui/material'
import { Add, Edit, Delete, Key, Settings } from '@mui/icons-material'
import { useGetCompaniesQuery, useCreateCompanyMutation } from '../store/apiSlice'
import { Company } from '../types'

const CompanyMDM: React.FC = () => {
  const { data: companies, isLoading, refetch } = useGetCompaniesQuery()
  const [createCompany] = useCreateCompanyMutation()
  const [openDialog, setOpenDialog] = useState(false)
  const [editingCompany, setEditingCompany] = useState<Company | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    domain: '',
    mdmEnabled: false,
    apiKey: '',
    settings: {
      autoRetry: true,
      maxRetries: 3,
      webhookUrl: '',
    },
  })

  const handleOpenDialog = (company?: Company) => {
    if (company) {
      setEditingCompany(company)
      setFormData({
        name: company.name,
        domain: company.domain,
        mdmEnabled: company.mdmEnabled,
        apiKey: company.apiKey || '',
        settings: company.settings || {
          autoRetry: true,
          maxRetries: 3,
          webhookUrl: '',
        },
      })
    } else {
      setEditingCompany(null)
      setFormData({
        name: '',
        domain: '',
        mdmEnabled: false,
        apiKey: '',
        settings: {
          autoRetry: true,
          maxRetries: 3,
          webhookUrl: '',
        },
      })
    }
    setOpenDialog(true)
  }

  const handleCloseDialog = () => {
    setOpenDialog(false)
    setEditingCompany(null)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, checked } = e.target
    if (name === 'mdmEnabled') {
      setFormData(prev => ({ ...prev, [name]: checked }))
    } else if (name.startsWith('settings.')) {
      const settingName = name.split('.')[1]
      setFormData(prev => ({
        ...prev,
        settings: {
          ...prev.settings,
          [settingName]: value,
        },
      }))
    } else {
      setFormData(prev => ({ ...prev, [name]: value }))
    }
  }

  const handleSubmit = async () => {
    try {
      if (editingCompany) {
        // Update existing company (would need updateCompany mutation)
        console.log('Update company:', formData)
      } else {
        // Create new company
        await createCompany(formData).unwrap()
      }
      handleCloseDialog()
      refetch()
    } catch (error) {
      console.error('Failed to save company:', error)
    }
  }

  const generateApiKey = () => {
    const key = 'vk_' + Array.from({ length: 32 }, () => 
      Math.random().toString(36).charAt(2)
    ).join('')
    setFormData(prev => ({ ...prev, apiKey: key }))
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          Company MDM Management
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => handleOpenDialog()}
        >
          Add Company
        </Button>
      </Box>

      <Alert severity="info" sx={{ mb: 3 }}>
        Manage company configurations, API keys, and MDM settings for job processing.
      </Alert>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Company Name</TableCell>
              <TableCell>Domain</TableCell>
              <TableCell>MDM Status</TableCell>
              <TableCell>API Key</TableCell>
              <TableCell>Job Count</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  Loading...
                </TableCell>
              </TableRow>
            ) : companies?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  No companies found. Add your first company to get started.
                </TableCell>
              </TableRow>
            ) : (
              companies?.map((company) => (
                <TableRow key={company.id}>
                  <TableCell>{company.name}</TableCell>
                  <TableCell>{company.domain}</TableCell>
                  <TableCell>
                    <Chip
                      label={company.mdmEnabled ? 'Enabled' : 'Disabled'}
                      color={company.mdmEnabled ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {company.apiKey ? (
                      <Chip
                        icon={<Key />}
                        label={`${company.apiKey.substring(0, 10)}...`}
                        size="small"
                        variant="outlined"
                      />
                    ) : (
                      <Typography variant="body2" color="textSecondary">
                        Not configured
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>{company.jobCount || 0}</TableCell>
                  <TableCell>{new Date(company.createdAt).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={1}>
                      <IconButton
                        size="small"
                        onClick={() => handleOpenDialog(company)}
                      >
                        <Edit fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleOpenDialog(company)}
                      >
                        <Settings fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        color="error"
                      >
                        <Delete fontSize="small" />
                      </IconButton>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Add/Edit Company Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingCompany ? 'Edit Company' : 'Add New Company'}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 2 }}>
            <TextField
              fullWidth
              label="Company Name"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              required
            />
            <TextField
              fullWidth
              label="Domain"
              name="domain"
              value={formData.domain}
              onChange={handleInputChange}
              required
              placeholder="example.com"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={formData.mdmEnabled}
                  onChange={handleInputChange}
                  name="mdmEnabled"
                />
              }
              label="Enable MDM Integration"
            />
            <Box>
              <TextField
                fullWidth
                label="API Key"
                name="apiKey"
                value={formData.apiKey}
                onChange={handleInputChange}
                InputProps={{
                  endAdornment: (
                    <Button size="small" onClick={generateApiKey}>
                      Generate
                    </Button>
                  ),
                }}
              />
            </Box>
            <Typography variant="h6">Advanced Settings</Typography>
            <FormControlLabel
              control={
                <Switch
                  checked={formData.settings.autoRetry}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    settings: { ...prev.settings, autoRetry: e.target.checked }
                  }))}
                />
              }
              label="Auto Retry Failed Jobs"
            />
            <TextField
              fullWidth
              label="Max Retries"
              name="settings.maxRetries"
              type="number"
              value={formData.settings.maxRetries}
              onChange={handleInputChange}
              inputProps={{ min: 0, max: 10 }}
            />
            <TextField
              fullWidth
              label="Webhook URL"
              name="settings.webhookUrl"
              value={formData.settings.webhookUrl}
              onChange={handleInputChange}
              placeholder="https://example.com/webhook"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained">
            {editingCompany ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default CompanyMDM
