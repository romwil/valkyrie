# Valkyrie Web UI

Modern React TypeScript web interface for the Valkyrie Job Processing System.

## Features

- **Dashboard**: Real-time job statistics and monitoring
- **Job Creation**: Create and upload jobs with priority settings
- **Job Monitoring**: Live job tracking with WebSocket updates
- **Company MDM**: Manage company configurations and API keys
- **Analytics**: Comprehensive charts and performance metrics

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and optimized builds
- **Material-UI** for modern UI components
- **Redux Toolkit** for state management
- **RTK Query** for efficient API data fetching
- **Recharts** for data visualization
- **Socket.io** for real-time updates

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── components/       # React components
│   ├── Dashboard.tsx
│   ├── JobCreation.tsx
│   ├── JobMonitoring.tsx
│   ├── CompanyMDM.tsx
│   └── Analytics.tsx
├── store/           # Redux store and slices
│   ├── store.ts
│   ├── apiSlice.ts
│   ├── jobsSlice.ts
│   ├── companiesSlice.ts
│   └── analyticsSlice.ts
├── types/           # TypeScript type definitions
├── hooks/           # Custom React hooks
└── App.tsx          # Main application component
```

## API Integration

The web UI connects to the Valkyrie backend API at `http://localhost:8000`. Ensure the backend is running before starting the web UI.

## WebSocket Connection

Real-time job updates are received via WebSocket connection to `ws://localhost:8000/ws`.
