import DashboardLayout from '../layouts/DashboardLayout'
import { useFeatures } from '../hooks/useApi'
import { TableSkeleton } from '../components/ui/Skeleton'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'

export default function FeatureImportancePage() {
  const { data, isLoading } = useFeatures()

  const features = (data?.top_features || data || []).slice(0, 15).map(f => ({
    name: f.feature || f.name || '—',
    importance: parseFloat(f.importance || f.value || 0).toFixed(4)
  }))

  return (
    <DashboardLayout title="Feature Importance" subtitle="SHAP and permutation-based feature rankings">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div className="card">
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Top Impact Features</h3>
          {isLoading ? <TableSkeleton rows={10} /> : features.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={features} layout="vertical" margin={{ left: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 11, fill: '#0f172a' }} width={140} />
                <Tooltip />
                <Bar dataKey="importance" fill="#3b5bdb" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ textAlign: 'center', color: '#94a3b8', padding: 40 }}>
              Feature data not available. Run the training pipeline to generate SHAP values.
            </div>
          )}
        </div>
        <div className="card">
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Feature Table</h3>
          <table className="gp-table">
            <thead><tr><th>#</th><th>Feature</th><th>Importance</th><th>Type</th></tr></thead>
            <tbody>
              {features.map((f, i) => (
                <tr key={i}>
                  <td style={{ color: '#94a3b8' }}>{i + 1}</td>
                  <td style={{ fontWeight: 500 }}>{f.name}</td>
                  <td style={{ color: '#3b5bdb', fontWeight: 600 }}>{f.importance}</td>
                  <td><span className="badge badge-info">Statistics</span></td>
                </tr>
              ))}
              {features.length === 0 && <tr><td colSpan={4} style={{ textAlign: 'center', color: '#94a3b8', padding: 32 }}>No feature data yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </DashboardLayout>
  )
}
