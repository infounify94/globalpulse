import DashboardLayout from '../layouts/DashboardLayout'
import { useExperiments } from '../hooks/useApi'
import { TableSkeleton } from '../components/ui/Skeleton'
import { fmtDateTime } from '../utils/format'

export default function ExperimentsPage() {
  const { data, isLoading } = useExperiments()
  const experiments = Array.isArray(data) ? data : []

  return (
    <DashboardLayout title="Experiments" subtitle="All training runs, hyperparameters, and evaluation metrics">
      <div className="card">
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Experiment Registry</h3>
        {isLoading ? <TableSkeleton rows={10} /> : (
          <table className="gp-table">
            <thead>
              <tr>
                <th>Experiment ID</th>
                <th>Status</th>
                <th>Algorithm</th>
                <th>Dataset</th>
                <th>Feature Version</th>
                <th>Accuracy</th>
                <th>Brier Score</th>
                <th>Start Time (UTC)</th>
              </tr>
            </thead>
            <tbody>
              {experiments.map((e, i) => (
                <tr key={i}>
                  <td style={{ fontSize: 11, color: '#64748b', fontFamily: 'monospace' }}>
                    {e.id || '—'}
                  </td>
                  <td>
                    {e.status === 'COMPLETED' ? (
                      <span className="badge badge-success">Completed</span>
                    ) : (
                      <span className="badge badge-warn">Running</span>
                    )}
                  </td>
                  <td style={{ fontWeight: 600 }}>{e.algorithm}</td>
                  <td style={{ fontSize: 12, color: '#64748b' }}>{e.dataset_version}</td>
                  <td style={{ fontSize: 12, color: '#64748b' }}>{e.feature_version}</td>
                  <td style={{ color: '#16a34a', fontWeight: 700 }}>
                    {e.accuracy_mean != null ? `${(e.accuracy_mean * 100).toFixed(2)}%` : '—'}
                  </td>
                  <td>{e.brier_score != null ? e.brier_score.toFixed(4) : '—'}</td>
                  <td style={{ fontSize: 11, color: '#94a3b8' }}>{fmtDateTime(e.start_time)}</td>
                </tr>
              ))}
              {experiments.length === 0 && (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', color: '#94a3b8', padding: '40px 0' }}>
                    No experiments found. Run the training pipeline.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </DashboardLayout>
  )
}
