import DashboardLayout from '../layouts/DashboardLayout'
import { useExperiments } from '../hooks/useApi'
import { TableSkeleton } from '../components/ui/Skeleton'
import { fmtDate } from '../utils/format'

export default function ExperimentsPage() {
  const { data, isLoading } = useExperiments()
  const experiments = data?.experiments || (Array.isArray(data) ? data : [])

  return (
    <DashboardLayout title="Experiments" subtitle="All training runs, hyperparameters, and evaluation metrics">
      <div className="card">
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Experiment Registry</h3>
        {isLoading ? <TableSkeleton rows={10} /> : (
          <table className="gp-table">
            <thead>
              <tr><th>Run ID</th><th>Algorithm</th><th>Status</th><th>Accuracy</th><th>Brier</th><th>Dataset</th><th>Date</th></tr>
            </thead>
            <tbody>
              {experiments.map((e, i) => (
                <tr key={i}>
                  <td style={{ fontSize: 11, color: '#64748b', fontFamily: 'monospace' }}>{(e.id || '').slice(0, 12)}…</td>
                  <td style={{ fontWeight: 600 }}>{e.algorithm}</td>
                  <td>
                    <span className={`badge ${e.is_champion ? 'badge-success' : 'badge-info'}`}>
                      {e.is_champion ? 'Champion' : 'Challenger'}
                    </span>
                  </td>
                  <td style={{ color: '#16a34a', fontWeight: 700 }}>{e.accuracy_mean ? `${(e.accuracy_mean * 100).toFixed(2)}%` : '—'}</td>
                  <td>{e.brier_score ? e.brier_score.toFixed(4) : '—'}</td>
                  <td style={{ fontSize: 12, color: '#64748b' }}>{e.dataset_version || `${e.train_start_year}–${e.train_end_year}`}</td>
                  <td style={{ fontSize: 12, color: '#94a3b8' }}>{fmtDate(e.created_at)}</td>
                </tr>
              ))}
              {experiments.length === 0 && (
                <tr><td colSpan={7} style={{ textAlign: 'center', color: '#94a3b8', padding: 32 }}>No experiments yet.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </DashboardLayout>
  )
}
