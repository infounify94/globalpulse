import DashboardLayout from '../layouts/DashboardLayout'
import { useExperiments } from '../hooks/useApi'
import { TableSkeleton } from '../components/ui/Skeleton'
import { fmtDateTime } from '../utils/format'
import { AlertTriangle } from 'lucide-react'

// ─────────────────────────────────────────────────────────────────────────────
// Experiments Page
// Phase 11: All fields from experiment_registry joined with model_registry.
//   Run ID, Algorithm, Dataset, Features, Accuracy, AUC, Brier, Log Loss,
//   Duration, Status, Start Time
// Phase 15: No placeholders — empty state shown if no data.
// ─────────────────────────────────────────────────────────────────────────────
export default function ExperimentsPage() {
  const { data, isLoading } = useExperiments()
  const experiments = Array.isArray(data) ? data : []

  return (
    <DashboardLayout
      title="Experiments"
      subtitle="All training runs, hyperparameters, and evaluation metrics — from experiment_registry"
    >
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600 }}>Experiment Registry</h3>
          <span style={{ fontSize: 11, color: '#94a3b8' }}>{experiments.length} experiments</span>
        </div>
        {isLoading ? <TableSkeleton rows={10} /> : (
          <div style={{ overflowX: 'auto' }}>
            <table className="gp-table">
              <thead>
                <tr>
                  <th>Experiment ID</th>
                  <th>Status</th>
                  <th>Algorithm</th>
                  <th>Dataset</th>
                  <th>Feature Version</th>
                  <th>Accuracy</th>
                  <th>AUC ROC</th>
                  <th>Brier Score</th>
                  <th>Log Loss</th>
                  <th>Duration</th>
                  <th>Start Time (UTC)</th>
                </tr>
              </thead>
              <tbody>
                {experiments.map((e, i) => (
                  <tr key={i}>
                    <td style={{ fontSize: 11, color: '#64748b', fontFamily: 'monospace', maxWidth: 160, wordBreak: 'break-all' }}>
                      {e.id || '—'}
                      {e.is_champion && (
                        <span className="badge badge-success" style={{ marginLeft: 6, fontSize: 9 }}>Champion</span>
                      )}
                    </td>
                    <td>
                      {e.status === 'COMPLETED'
                        ? <span className="badge badge-success">Completed</span>
                        : <span className="badge badge-warn">Running</span>}
                    </td>
                    <td style={{ fontWeight: 600 }}>{e.algorithm}</td>
                    <td style={{ fontSize: 12, color: '#64748b' }}>{e.dataset_version}</td>
                    <td style={{ fontSize: 12, color: '#64748b' }}>{e.feature_version}</td>
                    <td style={{ color: '#16a34a', fontWeight: 700 }}>
                      {e.accuracy_mean != null ? `${(e.accuracy_mean * 100).toFixed(2)}%` : '—'}
                    </td>
                    <td style={{ color: '#3b5bdb', fontWeight: 600 }}>
                      {e.auc_roc != null ? e.auc_roc.toFixed(4) : '—'}
                    </td>
                    <td>{e.brier_score != null ? e.brier_score.toFixed(4) : '—'}</td>
                    <td>{e.log_loss   != null ? e.log_loss.toFixed(4)   : '—'}</td>
                    <td style={{ fontSize: 12, color: '#475569', whiteSpace: 'nowrap' }}>
                      {e.duration || '—'}
                    </td>
                    <td style={{ fontSize: 11, color: '#94a3b8', whiteSpace: 'nowrap' }}>
                      {fmtDateTime(e.start_time)}
                    </td>
                  </tr>
                ))}
                {experiments.length === 0 && (
                  <tr>
                    <td colSpan={11} style={{ textAlign: 'center', color: '#94a3b8', padding: '40px 0' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                        <AlertTriangle size={24} color="#d97706" />
                        <div>No experiments found in experiment_registry.</div>
                        <div style={{ fontSize: 11 }}>Run the training pipeline to generate experiments.</div>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
