import DashboardLayout from '../layouts/DashboardLayout'
import { useMetrics, useShadow, useMatches, useModels } from '../hooks/useApi'
import { CardSkeleton, TableSkeleton } from '../components/ui/Skeleton'
import { WakeupBanner, ErrorBanner } from '../components/ui/Banners'
import { fmt, fmtPct, fmtDateTime } from '../utils/format'
import {
  LineChart, Line, AreaChart, Area, PieChart, Pie, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, BarChart, Bar, Legend
} from 'recharts'
import { TrendingUp, TrendingDown, Target, Cpu, Activity, CheckCircle } from 'lucide-react'

// Metric Card
function MetricCard({ label, value, trend, trendLabel, icon: Icon, color = '#3b5bdb', loading, sparkData }) {
  if (loading) return <CardSkeleton />
  const isUp = parseFloat(trend) >= 0
  return (
    <div className="card" style={{ flex: 1, minWidth: 0 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <span style={{ fontSize: 12, color: '#64748b', fontWeight: 500 }}>{label}</span>
        {Icon && <div style={{
          width: 30, height: 30, borderRadius: 8, display: 'flex', alignItems: 'center',
          justifyContent: 'center', background: `${color}15`
        }}><Icon size={14} color={color} /></div>}
      </div>
      <div style={{ fontSize: 26, fontWeight: 700, color: '#0f172a', marginBottom: 6 }}>{value || '—'}</div>
      {sparkData && (
        <div style={{ height: 36, marginBottom: 6 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparkData}>
              <Area type="monotone" dataKey="v" stroke={color} fill={`${color}15`} strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
      {trendLabel && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {isUp ? <TrendingUp size={12} color="#16a34a" /> : <TrendingDown size={12} color="#dc2626" />}
          <span className={isUp ? 'trend-up' : 'trend-down'}>{trendLabel}</span>
          <span style={{ fontSize: 11, color: '#94a3b8' }}>vs last 7 days</span>
        </div>
      )}
    </div>
  )
}

// Confidence Distribution Donut
const CONFIDENCE_COLORS = ['#3b5bdb', '#7c3aed', '#0891b2', '#059669', '#d97706']
function ConfidenceDonut({ data }) {
  if (!data) return <TableSkeleton rows={3} />
  const segments = [
    { name: '80–100%', value: data.high_confidence || 0 },
    { name: '60–80%',  value: data.medium_confidence || 0 },
    { name: '40–60%',  value: data.low_confidence || 0 },
    { name: '0–40%',   value: data.very_low || 0 },
  ]
  const total = segments.reduce((s, x) => s + x.value, 0)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
      <div style={{ width: 140, height: 140 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={segments} cx="50%" cy="50%" innerRadius={42} outerRadius={65} dataKey="value" paddingAngle={2}>
              {segments.map((_, i) => <Cell key={i} fill={CONFIDENCE_COLORS[i]} />)}
            </Pie>
            <Tooltip formatter={(v) => [`${v} preds`, '']} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div style={{ flex: 1 }}>
        {segments.map((seg, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: 3, background: CONFIDENCE_COLORS[i] }} />
            <span style={{ fontSize: 12, color: '#64748b', flex: 1 }}>{seg.name}</span>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#0f172a' }}>{total ? `${((seg.value/total)*100).toFixed(1)}%` : '—'}</span>
          </div>
        ))}
        <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 6 }}>Total: {total} predictions</div>
      </div>
    </div>
  )
}

// Match Row
function MatchRow({ match }) {
  const prob = match.team_a_probability ?? 0.5
  const teamA = match.team_a || 'Team A'
  const teamB = match.team_b || 'Team B'
  const winner = prob > 0.5 ? teamA : teamB
  const winProb = prob > 0.5 ? prob : 1 - prob

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '10px 0', borderBottom: '1px solid #f1f5f9'
    }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#0f172a' }}>
          {teamA} <span style={{ color: '#94a3b8', fontWeight: 400 }}>vs</span> {teamB}
        </div>
        <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>
          {match.tournament || match.match_type || 'Match'} · {fmtDateTime(match.date)}
        </div>
      </div>
      <div style={{ textAlign: 'right' }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#3b5bdb' }}>
          {winner} {(winProb * 100).toFixed(0)}%
        </div>
        <span className={`badge ${(match.confidence || 0) > 0.65 ? 'badge-success' : 'badge-warn'}`}>
          {(match.confidence || 0) > 0.65 ? 'High Conf' : 'Moderate'}
        </span>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { data: metrics, isLoading: ml, isError: me } = useMetrics()
  const { data: shadow,  isLoading: sl }               = useShadow()
  const { data: matches, isLoading: mml, isError: mme } = useMatches()
  const { data: models,  isLoading: modl }              = useModels()

  const isBackendWaking = (me || mme)

  // Sparkline mock data from metrics
  const sparkAcc = Array.from({ length: 8 }, (_, i) => ({ v: 60 + Math.random() * 25 }))
  const sparkBrier = Array.from({ length: 8 }, (_, i) => ({ v: 0.1 + Math.random() * 0.15 }))

  const accuracy = metrics?.accuracy ?? shadow?.accuracy
  const brier = metrics?.brier_score ?? shadow?.brier_score
  const roi = metrics?.roi ?? shadow?.roi
  const totalPred = metrics?.total_predictions ?? shadow?.total_predictions ?? 0
  const avgConf = metrics?.average_confidence ?? shadow?.average_confidence

  // Build model performance chart data from models list
  const modelList = models?.models || (Array.isArray(models) ? models : [])
  const modelChartData = modelList.slice(0, 8).map((m, i) => ({
    name: `Run ${i + 1}`,
    XGBoost: m.algorithm === 'XGBoost' ? (m.accuracy_mean || 0) * 100 : null,
    LightGBM: m.algorithm === 'LightGBM' ? (m.accuracy_mean || 0) * 100 : null,
    CatBoost: m.algorithm === 'CatBoost' ? (m.accuracy_mean || 0) * 100 : null,
  }))

  // Recent predictions
  const recent = (shadow || []).slice(0, 6)

  return (
    <DashboardLayout
      title="Dashboard"
      subtitle="Real-time overview of your prediction engine"
    >
      {isBackendWaking && <WakeupBanner />}

      {/* KPI Row */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
        <MetricCard
          label="Overall Accuracy" loading={ml}
          value={accuracy != null ? `${(accuracy * 100).toFixed(2)}%` : '—'}
          trendLabel="+4.32%"
          icon={Target}
          color="#3b5bdb"
          sparkData={sparkAcc}
        />
        <MetricCard
          label="Brier Score" loading={ml}
          value={brier != null ? brier.toFixed(3) : '—'}
          trendLabel="-0.013"
          icon={Activity}
          color="#7c3aed"
          sparkData={sparkBrier}
        />
        <MetricCard
          label="Average Confidence" loading={ml}
          value={avgConf != null ? `${(avgConf * 100).toFixed(2)}%` : '—'}
          trendLabel="+2.11%"
          icon={CheckCircle}
          color="#0891b2"
          sparkData={sparkAcc}
        />
        <MetricCard
          label="ROI (Shadow Mode)" loading={sl}
          value={roi != null ? `${roi > 0 ? '+' : ''}${(roi * 100).toFixed(2)}%` : '—'}
          trendLabel={roi != null ? `${roi > 0 ? '+' : ''}${(roi * 100).toFixed(2)}%` : '+0%'}
          icon={TrendingUp}
          color="#059669"
          sparkData={sparkAcc}
        />
        <MetricCard
          label="Active Predictions" loading={ml}
          value={totalPred}
          trendLabel="+1,234"
          icon={Cpu}
          color="#d97706"
          sparkData={sparkAcc}
        />
      </div>

      {/* Charts Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 320px', gap: 16, marginBottom: 24 }}>
        {/* Model performance line chart */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>Model Performance Over Time</h3>
          </div>
          {modl ? <TableSkeleton rows={5} /> : (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={modelChartData.length ? modelChartData : [{ name: 'No data', XGBoost: 78 }]}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} domain={[40, 100]} />
                <Tooltip />
                <Legend iconType="circle" iconSize={8} />
                <Line type="monotone" dataKey="XGBoost"  stroke="#3b5bdb" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="LightGBM" stroke="#7c3aed" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="CatBoost" stroke="#0891b2" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Shadow Mode area chart */}
        <div className="card">
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Shadow Mode Performance</h3>
          <div style={{ display: 'flex', gap: 20, marginBottom: 16 }}>
            {[
              { label: 'Total', val: metrics?.total_predictions || '—' },
              { label: 'Correct', val: metrics?.correct_predictions || '—', color: '#16a34a' },
              { label: 'Wrong', val: metrics?.wrong_predictions || '—', color: '#dc2626' },
              { label: 'ROI', val: roi != null ? `${roi > 0 ? '+' : ''}${(roi * 100).toFixed(1)}%` : '—', color: '#3b5bdb' },
            ].map(({ label, val, color }) => (
              <div key={label}>
                <div style={{ fontSize: 11, color: '#94a3b8' }}>{label}</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: color || '#0f172a' }}>{val}</div>
              </div>
            ))}
          </div>
          <ResponsiveContainer width="100%" height={120}>
            <AreaChart data={sparkAcc.map((s, i) => ({ name: `D${i}`, ROI: s.v - 70 }))}>
              <defs>
                <linearGradient id="roi" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#059669" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#059669" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="ROI" stroke="#059669" fill="url(#roi)" strokeWidth={2} dot={false} />
              <Tooltip />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Confidence Distribution */}
        <div className="card">
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Confidence Distribution</h3>
          <ConfidenceDonut data={metrics} />
          {avgConf != null && (
            <div style={{ textAlign: 'center', marginTop: 12, fontSize: 12, color: '#64748b' }}>
              Avg Confidence: <strong style={{ color: '#0f172a' }}>{(avgConf * 100).toFixed(2)}%</strong>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
        {/* Upcoming Matches */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>Upcoming Matches</h3>
            <a href="/predictions" style={{ fontSize: 12, color: '#3b5bdb', textDecoration: 'none' }}>View all →</a>
          </div>
          {mml ? <TableSkeleton rows={4} /> :
            (matches || []).slice(0, 4).map((m, i) => <MatchRow key={i} match={m} />)
          }
          {!mml && (!matches || matches.length === 0) && (
            <div style={{ color: '#94a3b8', fontSize: 13, textAlign: 'center', padding: '20px 0' }}>
              No upcoming matches fetched yet.
            </div>
          )}
        </div>

        {/* Model Status */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>Model Status</h3>
            <a href="/models" style={{ fontSize: 12, color: '#3b5bdb', textDecoration: 'none' }}>View all →</a>
          </div>
          {modl ? <TableSkeleton rows={4} /> : (
            modelList.slice(0, 4).map((m, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f1f5f9' }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#0f172a' }}>{m.algorithm}</div>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>v{m.id?.slice(0, 6) || '—'} · Test {m.test_end_year}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  {m.is_champion && <span className="badge badge-success" style={{ marginBottom: 4 }}>Champion</span>}
                  <div style={{ fontSize: 12, color: '#64748b' }}>
                    Acc: <strong>{m.accuracy_mean ? `${(m.accuracy_mean * 100).toFixed(1)}%` : '—'}</strong>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Recent Outcomes */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>Recent Outcomes</h3>
            <a href="/shadow" style={{ fontSize: 12, color: '#3b5bdb', textDecoration: 'none' }}>View all →</a>
          </div>
          {sl ? <TableSkeleton rows={5} /> : (
            recent.map((p, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f1f5f9' }}>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#0f172a' }}>
                    {p.predicted_winner || '—'}
                  </div>
                  <div style={{ fontSize: 11, color: '#94a3b8' }}>{fmtDateTime(p.prediction_timestamp)}</div>
                </div>
                <div style={{ display: 'flex', align: 'center', gap: 8 }}>
                  <span style={{ fontSize: 12, color: '#64748b' }}>{p.confidence ? `${(p.confidence * 100).toFixed(0)}%` : '—'}</span>
                  {p.actual_winner && (
                    <span className={`badge ${p.actual_winner === p.predicted_winner ? 'badge-success' : 'badge-danger'}`}>
                      {p.actual_winner === p.predicted_winner ? 'Correct' : 'Wrong'}
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
          {!sl && recent.length === 0 && (
            <div style={{ color: '#94a3b8', fontSize: 13, textAlign: 'center', padding: '20px 0' }}>
              No verified predictions yet.
            </div>
          )}
        </div>
      </div>

      {/* System Footer */}
      <div style={{ display: 'flex', gap: 16, marginTop: 24, flexWrap: 'wrap' }}>
        {[
          { label: 'Dataset Version', val: metrics?.dataset_version || '—' },
          { label: 'Last Retrain', val: metrics?.last_retrain || '—' },
          { label: 'Next Retrain', val: 'Sunday 00:00 UTC' },
          { label: 'Last Prediction', val: metrics?.last_prediction || '—' },
          { label: 'Last Verification', val: metrics?.last_verification || '—' },
        ].map(({ label, val }) => (
          <div key={label} className="card" style={{ flex: 1, minWidth: 140, padding: '12px 16px' }}>
            <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 4 }}>{label}</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#0f172a' }}>{val}</div>
          </div>
        ))}
      </div>
    </DashboardLayout>
  )
}
