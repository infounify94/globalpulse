import DashboardLayout from '../layouts/DashboardLayout'
import { useFeatures } from '../hooks/useApi'
import { TableSkeleton } from '../components/ui/Skeleton'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import { AlertTriangle } from 'lucide-react'

// ─────────────────────────────────────────────────────────────────────────────
// Feature Importance Page — shows data from feature_importance table
// ─────────────────────────────────────────────────────────────────────────────
export default function FeatureImportancePage() {
  const { data, isLoading } = useFeatures()
  const features = Array.isArray(data) ? data : []

  return (
    <DashboardLayout title="Feature Importance" subtitle="SHAP and model-derived feature rankings">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Bar Chart */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>Top Impact Features</h3>
            <span style={{ fontSize: 11, color: '#94a3b8' }}>from feature_importance</span>
          </div>
          {isLoading ? <TableSkeleton rows={10} /> : features.length > 0 ? (
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={features} layout="vertical" margin={{ left: 40, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <YAxis dataKey="feature_name" type="category" tick={{ fontSize: 11, fill: '#0f172a' }} width={180} />
                <Tooltip formatter={(value, name) => [value, 'Importance']} />
                <Bar dataKey="importance" fill="#3b5bdb" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 400, color: '#94a3b8' }}>
              <AlertTriangle size={32} color="#d97706" style={{ marginBottom: 12 }} />
              <div>Feature data not available.</div>
              <div style={{ fontSize: 12, marginTop: 4 }}>Run the training pipeline to compute importances.</div>
            </div>
          )}
        </div>

        {/* Tabular View */}
        <div className="card">
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Feature Details</h3>
          {isLoading ? <TableSkeleton rows={10} /> : (
            <div style={{ maxHeight: 400, overflowY: 'auto' }}>
              <table className="gp-table">
                <thead style={{ position: 'sticky', top: 0, background: 'white' }}>
                  <tr>
                    <th>#</th>
                    <th>Feature Name</th>
                    <th>Importance</th>
                    <th>Type</th>
                  </tr>
                </thead>
                <tbody>
                  {features.map((f, i) => (
                    <tr key={i}>
                      <td style={{ color: '#94a3b8' }}>{i + 1}</td>
                      <td style={{ fontWeight: 500 }}>{f.feature_name}</td>
                      <td style={{ color: '#3b5bdb', fontWeight: 600 }}>{f.importance.toFixed(4)}</td>
                      <td>
                        <span className={`badge ${f.feature_type === 'ancient' ? 'badge-warn' : 'badge-info'}`}>
                          {f.feature_type}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {features.length === 0 && (
                    <tr>
                      <td colSpan={4} style={{ textAlign: 'center', color: '#94a3b8', padding: '40px 0' }}>
                        No feature data yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}
