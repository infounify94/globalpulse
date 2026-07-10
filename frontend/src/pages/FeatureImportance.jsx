import DashboardLayout from '../layouts/DashboardLayout'
import { useFeatures, useModels } from '../hooks/useApi'
import { TableSkeleton } from '../components/ui/Skeleton'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import { AlertTriangle } from 'lucide-react'
import { fmtDateTime } from '../utils/format'

// ─────────────────────────────────────────────────────────────────────────────
// Feature Importance Page
// Phase 12: Top 20 features from feature_importance table.
//   - Bar Chart: ranked by importance
//   - Table: feature_name, importance, shap_mean (if available), type, model
// Phase 15: No hardcoded values. Shows N/A when shap_mean not computed.
// ─────────────────────────────────────────────────────────────────────────────
export default function FeatureImportancePage() {
  const { data, isLoading } = useFeatures()
  const { data: models }    = useModels()
  const features = Array.isArray(data) ? data : []

  // Champion info for context
  const champion = Array.isArray(models) ? models.find(m => m.is_champion) : null
  const champVersion = features[0]?.model_version || champion?.model_version || null
  const champDate    = features[0]?.computed_at   || champion?.training_date  || null
  const hasShap      = features.some(f => f.shap_mean != null)

  return (
    <DashboardLayout
      title="Feature Importance"
      subtitle="Model-derived feature rankings from the champion model"
    >
      {/* Context banner */}
      {champVersion && (
        <div style={{ marginBottom: 16, padding: '10px 16px', background: '#f0f9ff', borderRadius: 8, borderLeft: '3px solid #0891b2', fontSize: 12 }}>
          <strong>Champion Model:</strong> {champVersion}
          {champDate && <span style={{ color: '#64748b', marginLeft: 12 }}>Computed: {fmtDateTime(champDate)}</span>}
          {!hasShap && (
            <span style={{ color: '#d97706', marginLeft: 12 }}>
              ⚠ SHAP values not yet computed — run <code>compute_shap.py</code> post-training
            </span>
          )}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Bar Chart */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>
              Top {features.length} Features by Importance
            </h3>
            <span style={{ fontSize: 11, color: '#94a3b8' }}>from feature_importance</span>
          </div>
          {isLoading ? <TableSkeleton rows={10} /> : features.length > 0 ? (
            <ResponsiveContainer width="100%" height={Math.max(300, features.length * 22)}>
              <BarChart data={features} layout="vertical" margin={{ left: 40, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#94a3b8' }} tickFormatter={v => v.toFixed(3)} />
                <YAxis dataKey="feature_name" type="category" tick={{ fontSize: 10, fill: '#0f172a' }} width={190} />
                <Tooltip
                  formatter={(value, name) => [value.toFixed(4), name === 'importance' ? 'Importance' : 'SHAP Mean']}
                  labelStyle={{ fontWeight: 600 }}
                />
                <Bar dataKey="importance" fill="#3b5bdb" radius={[0, 4, 4, 0]} name="Importance" />
                {hasShap && (
                  <Bar dataKey="shap_mean" fill="#7c3aed" radius={[0, 4, 4, 0]} name="SHAP Mean" />
                )}
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 300, color: '#94a3b8' }}>
              <AlertTriangle size={32} color="#d97706" style={{ marginBottom: 12 }} />
              <div>Feature importance data not available.</div>
              <div style={{ fontSize: 12, marginTop: 4 }}>
                Run the training pipeline to compute feature importances.
              </div>
            </div>
          )}
        </div>

        {/* Tabular View */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>Feature Details</h3>
            <span style={{ fontSize: 11, color: '#94a3b8' }}>{features.length} features</span>
          </div>
          {isLoading ? <TableSkeleton rows={10} /> : (
            <div style={{ maxHeight: 500, overflowY: 'auto' }}>
              <table className="gp-table">
                <thead style={{ position: 'sticky', top: 0, background: 'white', zIndex: 1 }}>
                  <tr>
                    <th>#</th>
                    <th>Feature Name</th>
                    <th>Importance</th>
                    <th>SHAP Mean</th>
                    <th>Type</th>
                  </tr>
                </thead>
                <tbody>
                  {features.map((f, i) => (
                    <tr key={i}>
                      <td style={{ color: '#94a3b8', width: 30 }}>{i + 1}</td>
                      <td style={{ fontWeight: 500, fontSize: 12 }}>{f.feature_name}</td>
                      <td style={{ color: '#3b5bdb', fontWeight: 600 }}>
                        {f.importance != null ? f.importance.toFixed(4) : '—'}
                      </td>
                      <td style={{ color: '#7c3aed' }}>
                        {f.shap_mean != null
                          ? f.shap_mean.toFixed(4)
                          : <span style={{ color: '#94a3b8', fontSize: 11 }}>N/A</span>}
                      </td>
                      <td>
                        <span className={`badge ${
                          f.feature_type === 'ancient' ? 'badge-warn' :
                          f.feature_type === 'statistical' ? 'badge-info' :
                          'badge-info'
                        }`}>
                          {f.feature_type || 'statistical'}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {features.length === 0 && (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', color: '#94a3b8', padding: '40px 0' }}>
                        No feature importance data in database yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
          {features.length > 0 && !hasShap && (
            <div style={{ marginTop: 12, padding: '8px 12px', background: '#fffbeb', borderRadius: 6, fontSize: 11, color: '#92400e' }}>
              SHAP Mean values are null — SHAP analysis not yet computed for this model version.
              Run <code>compute_shap.py</code> after training to populate these values.
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}
