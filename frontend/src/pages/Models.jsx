import DashboardLayout from '../layouts/DashboardLayout'
import { useModels } from '../hooks/useApi'
import { TableSkeleton } from '../components/ui/Skeleton'

export default function ModelsPage() {
  const { data: models, isLoading } = useModels()

  return (
    <DashboardLayout title="Models" subtitle="Model registry, leaderboard, and champion selection">
      <div className="card">
        <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Model Leaderboard</h3>
        {isLoading ? <TableSkeleton rows={8} /> : (
          <table className="gp-table">
            <thead>
              <tr><th>Status</th><th>Algorithm</th><th>Train Years</th><th>Test Year</th><th>Accuracy</th><th>Brier</th><th>Log Loss</th><th>AUC</th></tr>
            </thead>
            <tbody>
              {(models?.models || (Array.isArray(models) ? models : [])).map((m, i) => (
                <tr key={i}>
                  <td>{m.is_champion ? <span className="badge badge-success">🏆 Champion</span> : <span className="badge badge-info">Challenger</span>}</td>
                  <td style={{ fontWeight: 600 }}>{m.algorithm}</td>
                  <td style={{ color: '#64748b', fontSize: 12 }}>{m.train_start_year}–{m.train_end_year}</td>
                  <td style={{ fontWeight: 600 }}>{m.test_end_year}</td>
                  <td style={{ color: '#16a34a', fontWeight: 700 }}>{m.accuracy_mean ? `${(m.accuracy_mean * 100).toFixed(2)}%` : '—'}</td>
                  <td>{m.brier_score ? m.brier_score.toFixed(4) : '—'}</td>
                  <td>{m.log_loss ? m.log_loss.toFixed(4) : '—'}</td>
                  <td>{m.auc_roc ? m.auc_roc.toFixed(4) : '—'}</td>
                </tr>
              ))}
              {(!models || (models?.models || (Array.isArray(models) ? models : [])).length === 0) && (
                <tr><td colSpan={8} style={{ textAlign: 'center', color: '#94a3b8', padding: 32 }}>No models in registry yet. Run the training pipeline.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </DashboardLayout>
  )
}
