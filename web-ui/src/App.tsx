import React from 'react'
import { Box, Drawer, AppBar, Toolbar, Typography, List, ListItem, ListItemIcon, ListItemText, Container } from '@mui/material'
import { Dashboard, Work, Business, Analytics, Settings } from '@mui/icons-material'
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom'
import DashboardComponent from './components/Dashboard'
import JobCreation from './components/JobCreation'
import JobMonitoring from './components/JobMonitoring'
import CompanyMDM from './components/CompanyMDM'
import AnalyticsView from './components/Analytics'

const drawerWidth = 240

const menuItems = [
  { text: 'Dashboard', icon: <Dashboard />, path: '/dashboard' },
  { text: 'Create Job', icon: <Work />, path: '/create-job' },
  { text: 'Monitor Jobs', icon: <Work />, path: '/monitor-jobs' },
  { text: 'Company MDM', icon: <Business />, path: '/company-mdm' },
  { text: 'Analytics', icon: <Analytics />, path: '/analytics' },
]

function App() {
  return (
    <Router>
      <Box sx={{ display: 'flex' }}>
        <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
          <Toolbar>
            <Typography variant="h6" noWrap component="div">
              Valkyrie Job Processing System
            </Typography>
          </Toolbar>
        </AppBar>
        <Drawer
          variant="permanent"
          sx={{
            width: drawerWidth,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              boxSizing: 'border-box',
            },
          }}
        >
          <Toolbar />
          <Box sx={{ overflow: 'auto' }}>
            <List>
              {menuItems.map((item) => (
                <ListItem button key={item.text} component={Link} to={item.path}>
                  <ListItemIcon>{item.icon}</ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItem>
              ))}
            </List>
          </Box>
        </Drawer>
        <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
          <Toolbar />
          <Container maxWidth="xl">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<DashboardComponent />} />
              <Route path="/create-job" element={<JobCreation />} />
              <Route path="/monitor-jobs" element={<JobMonitoring />} />
              <Route path="/company-mdm" element={<CompanyMDM />} />
              <Route path="/analytics" element={<AnalyticsView />} />
            </Routes>
          </Container>
        </Box>
      </Box>
    </Router>
  )
}

export default App
