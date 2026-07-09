import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'
import PredictionsPage from './pages/Predictions'
import ShadowModePage from './pages/ShadowMode'
import ModelsPage from './pages/Models'
import ExperimentsPage from './pages/Experiments'
import FeatureImportancePage from './pages/FeatureImportance'
import ErrorBoundary from './components/ErrorBoundary'
import {
  PatternMemoryPage, HistoricalReplayPage,
  ResearchPage, AlertsPage, SettingsPage
} from './pages/ShellPages'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 60000,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
    },
  },
})

export default function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route path="/"           element={<Dashboard />} />
          <Route path="/predictions" element={<PredictionsPage />} />
          <Route path="/shadow"     element={<ShadowModePage />} />
          <Route path="/models"     element={<ModelsPage />} />
          <Route path="/experiments" element={<ExperimentsPage />} />
          <Route path="/features"   element={<FeatureImportancePage />} />
          <Route path="/patterns"   element={<PatternMemoryPage />} />
          <Route path="/history"    element={<HistoricalReplayPage />} />
          <Route path="/research"   element={<ResearchPage />} />
          <Route path="/alerts"     element={<AlertsPage />} />
          <Route path="/settings"   element={<SettingsPage />} />
        </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}
