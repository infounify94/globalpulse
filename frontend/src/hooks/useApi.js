import { useQuery } from '@tanstack/react-query'
import {
  fetchStatus, fetchMetrics, fetchShadow,
  fetchMatches, fetchModels, fetchExperiments,
  fetchFeatures, fetchHistory,
} from '../api/endpoints'

export const useStatus      = () => useQuery({ queryKey: ['status'],      queryFn: fetchStatus,      retry: 3, staleTime: 30000 })
export const useMetrics     = () => useQuery({ queryKey: ['metrics'],      queryFn: fetchMetrics,     retry: 3, staleTime: 60000 })
export const useShadow      = () => useQuery({ queryKey: ['shadow'],       queryFn: fetchShadow,      retry: 3, staleTime: 60000 })
export const useMatches     = (p) => useQuery({ queryKey: ['matches', p],  queryFn: () => fetchMatches(p), retry: 3, staleTime: 120000 })
export const useModels      = () => useQuery({ queryKey: ['models'],       queryFn: fetchModels,      retry: 3, staleTime: 120000 })
export const useExperiments = () => useQuery({ queryKey: ['experiments'],  queryFn: fetchExperiments, retry: 3, staleTime: 120000 })
export const useFeatures    = () => useQuery({ queryKey: ['features'],     queryFn: fetchFeatures,    retry: 3, staleTime: 120000 })
export const useHistory     = () => useQuery({ queryKey: ['history'],      queryFn: fetchHistory,     retry: 3, staleTime: 60000 })
