import DashboardLayout from '../layouts/DashboardLayout'
import { useModels } from '../hooks/useApi'
import { TableSkeleton } from '../components/ui/Skeleton'
import { fmtDateTime } from '../utils/format'

export default function ModelsPage() {
  const { data: models, isLoading } = useModels()
  const modelList = Array.isArray(models) ? models : []

  return (
    <DashboardLayout title="Model Registry" subtitle="Historical models, leaderboard, and current champion">
      <div className="card">
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Leaderboard</h3>
        {isLoading ? <TableSkeleton rows={8} /> : (
          <table className="gp-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Version</th>
                <th>Algorithm</th>
                <th>Dataset</th>
                <th>Accuracy</th>
                <th>Brier</th>
                <th>Log Loss</th>
                <th>AUC ROC</th>
                <th>Training Date (UTC)</th>
              </tr>
            </thead>
            <tbody>
              {modelList.map((m, i) => (
                <tr key={i}>
                  <td>
                    {m.is_champion ? (
                      <span className="badge badge-success">🏆 Champion</span>
                    ) : (
                      <span className="badge badge-info">Challenger</span>
                    )}
                  </td>
                  <td style={{ fontFamily: 'monospace', fontSize: 11, color: '#64748b' }}>
                    {m.model_version ? m.model_version.slice(0, 15) + '…' : '—'}
                  </td>
                  <td style={{ fontWeight: 600 }}>{m.algorithm || '—'}</td>
                  <td style={{ color: '#64748b', fontSize: 12 }}>{m.dataset_version || '—'}</td>
                  <td style={{ color: '#16a34a', fontWeight: 700 }}>
                    {m.accuracy_mean != null ? `${(m.accuracy_mean * 100).toFixed(2)}%` : '—'}
                  </td>
                  <td>{m.brier_score != null ? m.brier_score.toFixed(4) : '—'}</td>
                  <td>{m.log_loss != null ? m.log_loss.toFixed(4) : '—'}</td>
                  <td>{m.auc_roc != null ? m.auc_roc.toFixed(4) : '—'}</td>
                  <td style={{ fontSize: 11, color: '#94a3b8' }}>
                    {fmtDateTime(m.training_date)}
                  </td>
                </tr>
              ))}
              {modelList.length === 0 && (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', color: '#94a3b8', padding: '40px 0' }}>
                    No models found in the registry. Run the training pipeline.
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
