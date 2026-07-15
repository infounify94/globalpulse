import DashboardLayout from '../layouts/DashboardLayout'
import { useModels } from '../hooks/useApi'
import { TableSkeleton } from '../components/ui/Skeleton'
import { fmtDateTime } from '../utils/format'
import { AlertTriangle } from 'lucide-react'

// ─────────────────────────────────────────────────────────────────────────────
// Models Page
// Phase 6: Full model_registry audit.
//   - Only one champion (enforced in fetchModels)
//   - All metrics: Accuracy, AUC, Brier, LogLoss, Calibration
//   - Training date, checksum, model version, dataset, feature families
// ─────────────────────────────────────────────────────────────────────────────
export default function ModelsPage() {
  const { data: models, isLoading } = useModels()
  const modelList = Array.isArray(models) ? models : []

  const champions   = modelList.filter(m => m.is_champion)
  const challengers = modelList.filter(m => !m.is_champion)
  const champion    = champions[0] || null

  const integrityViolation = champions.length > 1

  return (
    <DashboardLayout
      title="Model Registry"
      subtitle="Historical models, leaderboard, and current champion — from model_registry"
    >
      {integrityViolation && (
        <div style={{ marginBottom: 16, padding: '12px 16px', background: '#fef2f2', borderRadius: 8, borderLeft: '3px solid #dc2626', fontSize: 12, color: '#dc2626', fontWeight: 600 }}>
          ⚠ INTEGRITY VIOLATION: {champions.length} champion models found — must be exactly 1. Contact the ML team.
        </div>
      )}

      {/* Phase 6: Champion detail card */}
      {champion && (
        <div className="glass-card" style={{ marginBottom: 24, borderLeft: '3px solid #16a34a' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span className="badge badge-success" style={{ fontSize: 12 }}>🏆 Current Champion</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text)' }}>{champion.algorithm}</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '8px 24px' }}>
                {[
                  { label: 'Model Version',   val: champion.model_version || '—' },
                  { label: 'Dataset Version',  val: champion.dataset_version || '—' },
                  { label: 'Checksum',         val: champion.checksum ? champion.checksum.slice(0, 20) + '…' : '—' },
                  { label: 'Training Date',    val: fmtDateTime(champion.training_date) },
                ].map(({ label, val }) => (
                  <div key={label}>
                    <div style={{ fontSize: 10, color: 'var(--color-muted)', fontWeight: 500 }}>{label}</div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text)', fontFamily: label.includes('Version') || label === 'Checksum' ? 'monospace' : 'inherit', wordBreak: 'break-all' }}>{val}</div>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              {[
                { label: 'Accuracy',    val: champion.accuracy_mean != null ? `${(champion.accuracy_mean * 100).toFixed(2)}%` : '—', color: '#16a34a' },
                { label: 'AUC ROC',    val: champion.auc_roc       != null ? champion.auc_roc.toFixed(4)    : '—', color: '#3b5bdb' },
                { label: 'Brier',      val: champion.brier_score   != null ? champion.brier_score.toFixed(4) : '—', color: '#7c3aed' },
                { label: 'Log Loss',   val: champion.log_loss      != null ? champion.log_loss.toFixed(4)   : '—', color: '#0891b2' },
              ].map(({ label, val, color }) => (
                <div key={label} style={{ textAlign: 'center', minWidth: 90, padding: '0 8px' }}>
                  <div style={{ fontSize: 10, color: 'var(--color-muted)', marginBottom: 4 }}>{label}</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color }}>{val}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Full Leaderboard */}
      <div className="glass-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600 }}>Full Leaderboard</h3>
          <span style={{ fontSize: 11, color: 'var(--color-muted)' }}>
            {champions.length} champion · {challengers.length} challengers · {modelList.length} total
          </span>
        </div>
        {isLoading ? <TableSkeleton rows={8} /> : (
          <div style={{ overflowX: 'auto' }}>
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
                  <th>Checksum</th>
                  <th>Training Date (UTC)</th>
                </tr>
              </thead>
              <tbody>
                {modelList.map((m, i) => (
                  <tr key={i} style={m.is_champion ? { background: '#f0fdf4' } : {}}>
                    <td>
                      {m.is_champion
                        ? <span className="badge badge-success">🏆 Champion</span>
                        : <span className="badge badge-info">Challenger</span>}
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: 10, color: 'var(--color-muted)', maxWidth: 140, wordBreak: 'break-all' }}>
                      {m.model_version ? m.model_version.slice(0, 22) + (m.model_version.length > 22 ? '…' : '') : '—'}
                    </td>
                    <td style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>{m.algorithm || '—'}</td>
                    <td style={{ color: 'var(--color-muted)', fontSize: 12 }}>{m.dataset_version || '—'}</td>
                    <td style={{ color: '#16a34a', fontWeight: 700 }}>
                      {m.accuracy_mean != null ? `${(m.accuracy_mean * 100).toFixed(2)}%` : '—'}
                    </td>
                    <td>{m.brier_score != null ? m.brier_score.toFixed(4) : '—'}</td>
                    <td>{m.log_loss    != null ? m.log_loss.toFixed(4)    : '—'}</td>
                    <td style={{ color: '#3b5bdb', fontWeight: 600 }}>
                      {m.auc_roc != null ? m.auc_roc.toFixed(4) : '—'}
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: 10, color: 'var(--color-muted)' }}>
                      {m.checksum ? m.checksum.slice(0, 16) + '…' : '—'}
                    </td>
                    <td style={{ fontSize: 11, color: 'var(--color-muted)', whiteSpace: 'nowrap' }}>
                      {fmtDateTime(m.training_date)}
                    </td>
                  </tr>
                ))}
                {modelList.length === 0 && (
                  <tr>
                    <td colSpan={10} style={{ textAlign: 'center', color: 'var(--color-muted)', padding: '40px 0' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                        <AlertTriangle size={24} color="#d97706" />
                        <div>No models found in registry.</div>
                        <div style={{ fontSize: 11 }}>Run the training pipeline to register models.</div>
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
