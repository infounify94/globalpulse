import DashboardLayout from '../layouts/DashboardLayout'
import { useMetrics, useShadow, useMatches, useModels } from '../hooks/useApi'
import { CardSkeleton, TableSkeleton } from '../components/ui/Skeleton'
import { MetricCard } from '../components/ui/MetricCard'
import { WakeupBanner } from '../components/ui/Banners'
import { fmtDateTime } from '../utils/format'
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Legend,
} from 'recharts'
import { TrendingUp, Target, Cpu, Activity, CheckCircle, AlertTriangle } from 'lucide-react'

// ─────────────────────────────────────────────────────────────────────────────
// Confidence Distribution Donut — from dashboard_summary.confidence buckets
// ─────────────────────────────────────────────────────────────────────────────
const CONF_COLORS = ['#3b5bdb', '#7c3aed', '#0891b2', '#059669']
function ConfidenceDonut({ data }) {
  if (!data) return <TableSkeleton rows={3} />
  const segments = [
    { name: '80–100%', value: data.high_confidence   || 0 },
    { name: '60–80%',  value: data.medium_confidence || 0 },
    { name: '40–60%',  value: data.low_confidence    || 0 },
    { name: '0–40%',   value: data.very_low          || 0 },
  ]
  const total = segments.reduce((s, x) => s + x.value, 0)
  if (total === 0) {
    return (
      <div style={{ color: 'var(--color-muted)', fontSize: 12, textAlign: 'center', padding: 24 }}>
        Confidence distribution not yet computed.<br />
        <span style={{ fontSize: 11 }}>Run the training pipeline to generate this data.</span>
      </div>
    )
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
      <div style={{ width: 140, height: 140 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={segments} cx="50%" cy="50%" innerRadius={42} outerRadius={65} dataKey="value" paddingAngle={2}>
              {segments.map((_, i) => <Cell key={i} fill={CONF_COLORS[i]} />)}
            </Pie>
            <Tooltip formatter={(v) => [`${v} predictions`, '']} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div style={{ flex: 1 }}>
        {segments.map((seg, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <div style={{ width: 10, height: 10, borderRadius: 3, background: CONF_COLORS[i] }} />
            <span style={{ fontSize: 12, color: 'var(--color-muted)', flex: 1 }}>{seg.name}</span>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text)' }}>
              {total ? `${((seg.value / total) * 100).toFixed(1)}%` : '—'}
            </span>
          </div>
        ))}
        <div style={{ fontSize: 11, color: 'var(--color-muted)', marginTop: 6 }}>Total: {total} predictions</div>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Match Row — Upcoming matches from prediction_store PENDING + future date
// Phase 8: Shows team, venue, date (with year+UTC), confidence, top factors
// Phase 15: NO fabricated data — if top_driving_features is null, shows nothing
// ─────────────────────────────────────────────────────────────────────────────
function MatchRow({ match }) {
  // Phase 9 fix: Never synthesize winner from probability. Show '—' if null.
  const teamA = match.team_a || 'Unknown Team A'
  const teamB = match.team_b || 'Unknown Team B'
  const winner = match.predicted_winner || null
  const winProb = match.probability ?? null
  const venueStr = match.venue || null
  const topFactors = match.top_driving_features  // null if no real data — do not fake it

  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 12,
      padding: '12px 0', borderBottom: '1px solid var(--color-border)'
    }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text)' }}>
          {teamA} <span style={{ color: 'var(--color-muted)', fontWeight: 400 }}>vs</span> {teamB}
        </div>
        <div style={{ fontSize: 11, color: 'var(--color-muted)', marginTop: 2 }}>
          {venueStr && <strong style={{ color: '#475569' }}>{venueStr} · </strong>}
          {match.match_type || 'Cricket'} · {fmtDateTime(match.date)}
        </div>
        {/* Phase 12: Only show real factors from DB — never fabricated */}
        {topFactors && topFactors.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
            <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--color-muted)', marginRight: 2 }}>Top Factors:</span>
            {topFactors.slice(0, 4).map((f, i) => (
              <span key={i} style={{
                fontSize: 10, background: 'var(--color-surface)', border: '1px solid #e2e8f0',
                padding: '1px 5px', borderRadius: 4, color: '#334155'
              }}>
                ✓ {f.name} <strong style={{ color: '#16a34a' }}>({f.impact})</strong>
              </span>
            ))}
          </div>
        )}
      </div>
      <div style={{ textAlign: 'right', minWidth: 90 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#3b5bdb' }}>
          {winner
            ? `${winner}${winProb != null ? ` ${(winProb * 100).toFixed(0)}%` : ''}`
            : '—'
          }
        </div>
        {match.confidence != null && (
          <span
            className={`badge ${match.confidence > 0.65 ? 'badge-success' : 'badge-warn'}`}
            style={{ display: 'inline-block', marginTop: 4 }}
          >
            {match.confidence > 0.65 ? 'High Conf' : 'Moderate'}
          </span>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Dashboard Page
// ─────────────────────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { data: metrics, isLoading: ml, isError: me } = useMetrics()
  const { data: shadow,  isLoading: sl }               = useShadow()
  const { data: matches, isLoading: mml, isError: mme } = useMatches()
  const { data: models,  isLoading: modl }              = useModels()

  const isBackendError = me || mme

  // All values from backend — no frontend calculations
  const accuracy   = metrics?.accuracy    ?? null
  const brier      = metrics?.brier_score ?? null
  const roi        = metrics?.roi         ?? null
  const totalPred  = metrics?.total_predictions ?? null
  const avgConf    = metrics?.average_confidence ?? null

  // Model chart: real data from model_registry
  const modelList = Array.isArray(models) ? models : []
  const modelChartData = modelList
    .filter(m => m.accuracy_mean != null)
    .slice(0, 10)
    .reverse()
    .map((m, i) => ({
      name: m.training_date ? new Date(m.training_date).toLocaleDateString('en-GB', { month: 'short', day: '2-digit' }) : `Run ${i + 1}`,
      Accuracy: m.accuracy_mean != null ? parseFloat((m.accuracy_mean * 100).toFixed(2)) : null,
      AUC: m.auc_roc != null ? parseFloat((m.auc_roc * 100).toFixed(2)) : null,
      is_champion: m.is_champion,
    }))

  // Recent outcomes: from shadow (verified, past)
  const recent = (Array.isArray(shadow) ? shadow : []).slice(0, 6)

  return (
    <DashboardLayout title="Dashboard" subtitle="Real-time overview — all metrics sourced from production database">
      {isBackendError && <WakeupBanner />}

      {/* KPI Row — all from dashboard_summary view */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
        <MetricCard
          label="Verified Accuracy" loading={ml}
          value={accuracy != null ? `${(accuracy * 100).toFixed(2)}%` : null}
          sub="correct / verified predictions"
          icon={Target} color="#3b5bdb"
        />
        <MetricCard
          label="Brier Score" loading={ml}
          value={brier != null ? brier.toFixed(4) : null}
          sub="lower is better (0 = perfect)"
          icon={Activity} color="#7c3aed"
        />
        <MetricCard
          label="Avg Confidence" loading={ml}
          value={avgConf != null ? `${(avgConf * 100).toFixed(2)}%` : null}
          sub="mean prediction confidence"
          icon={CheckCircle} color="#0891b2"
        />
        <MetricCard
          label="ROI (Shadow)" loading={ml}
          value={roi != null ? `${roi > 0 ? '+' : ''}${(roi * 100).toFixed(2)}%` : null}
          sub="simulated betting return"
          icon={TrendingUp} color="#059669"
        />
        <MetricCard
          label="Total Predictions" loading={ml}
          value={totalPred != null ? totalPred.toLocaleString() : null}
          sub="all-time in production DB"
          icon={Cpu} color="#d97706"
        />
      </div>

      {/* Charts Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 16, marginBottom: 24 }}>
        {/* Model Performance Chart — real model_registry data */}
        <div className="glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>Model Performance History</h3>
            <span style={{ fontSize: 11, color: 'var(--color-muted)' }}>from model_registry</span>
          </div>
          {modl ? <TableSkeleton rows={5} /> : modelChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={modelChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--color-muted)' }} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--color-muted)' }} domain={[40, 100]} unit="%" />
                <Tooltip formatter={(v, n) => [`${v}%`, n]} />
                <Legend iconType="circle" iconSize={8} />
                <Line type="monotone" dataKey="Accuracy" stroke="#3b5bdb" strokeWidth={2} dot={{ r: 3 }} connectNulls />
                <Line type="monotone" dataKey="AUC" stroke="#7c3aed" strokeWidth={2} dot={{ r: 3 }} connectNulls />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ textAlign: 'center', color: 'var(--color-muted)', padding: '40px 0', fontSize: 13 }}>
              No model history yet. Run the training pipeline.
            </div>
          )}
        </div>

        {/* Confidence Distribution — from dashboard_summary */}
        <div className="glass-card">
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Confidence Distribution</h3>
          <ConfidenceDonut data={metrics} />
          {avgConf != null && (
            <div style={{ textAlign: 'center', marginTop: 12, fontSize: 12, color: 'var(--color-muted)' }}>
              Avg Confidence: <strong style={{ color: 'var(--color-text)' }}>{(avgConf * 100).toFixed(2)}%</strong>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
        {/* Upcoming Matches — ONLY real future PENDING from DB */}
        <div className="glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>Upcoming Matches</h3>
            <a href="/predictions" style={{ fontSize: 12, color: '#3b5bdb', textDecoration: 'none' }}>View all →</a>
          </div>
          {mml ? <TableSkeleton rows={4} /> :
            (Array.isArray(matches) ? matches : []).length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>Match</th>
                <th>Date</th>
                <th>Probability</th>
                <th>Confidence</th>
                <th>Recommendation</th>
                <th>Actual</th>
                <th>Result</th>
                <th>Reasons</th>
              </tr>
            </thead>
            <tbody>
              {matches.map(r => (
                <tr key={r.id}>
                  <td>
                    <div style={{ fontWeight: 500, color: 'var(--color-text)' }}>{r.team1} vs {r.team2}</div>
                    <div style={{ fontSize: 11, color: 'var(--color-muted)' }}>{r.venue}</div>
                  </td>
                  <td style={{ fontSize: 12, color: 'var(--color-muted)' }}>{fmtDateTime(r.match_date)}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div style={{ width: 40, height: 4, background: 'var(--color-border)', borderRadius: 2, overflow: 'hidden' }}>
                        <div style={{ height: '100%', background: '#3b5bdb', width: `${Math.round(r.probability * 100)}%` }} />
                      </div>
                      <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--color-text)' }}>{Math.round(r.probability * 100)}%</span>
                    </div>
                  </td>
                  <td>
                    <span style={{
                      padding: '2px 6px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                      background: r.confidence === 'HIGH' ? '#dcfce7' : r.confidence === 'MEDIUM' ? '#fef08a' : '#fee2e2',
                      color: r.confidence === 'HIGH' ? '#166534' : r.confidence === 'MEDIUM' ? '#854d0e' : '#991b1b'
                    }}>
                      {r.confidence || "WAITING"}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontWeight: 600, fontSize: 12, color: r.recommendation === '✅ BET' ? '#166534' : 'var(--color-muted)' }}>
                      {r.recommendation || "N/A"}
                    </span>
                  </td>
                  <td style={{ fontSize: 12, color: 'var(--color-text)' }}>{r.actual_winner || '—'}</td>
                  <td>
                    {r.actual_winner ? (
                      r.actual_winner === r.predicted_winner
                        ? <CheckCircle size={14} color="#10b981" />
                        : <AlertTriangle size={14} color="#ef4444" />
                    ) : <span style={{ fontSize: 12, color: 'var(--color-muted)' }}>Pending</span>}
                  </td>
                  <td style={{ fontSize: 10, color: 'var(--color-muted)', maxWidth: 150 }}>
                    {(r.reasons || []).join(", ") || "No reasons generated."}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
            ) : (
            <div style={{ color: 'var(--color-muted)', fontSize: 12, padding: '20px 0', textAlign: 'center' }}>
              <AlertTriangle size={20} style={{ marginBottom: 8, color: '#d97706' }} />
              <div>No upcoming predictions in database.</div>
              <div style={{ fontSize: 11, marginTop: 4 }}>Run <code>run_predict.py</code> via GitHub Actions to generate predictions.</div>
            </div>
          )}
        </div>

        {/* Model Status — from model_registry */}
        <div className="glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>Model Status</h3>
            <a href="/models" style={{ fontSize: 12, color: '#3b5bdb', textDecoration: 'none' }}>View all →</a>
          </div>
          {modl ? <TableSkeleton rows={4} /> : (
            modelList.slice(0, 4).map((m, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--color-border)' }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text)' }}>{m.algorithm}</div>
                  <div style={{ fontSize: 11, color: 'var(--color-muted)' }}>
                    {m.dataset_version || '—'} · {m.training_date ? new Date(m.training_date).getFullYear() : '—'}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  {m.is_champion && <span className="badge badge-success" style={{ marginBottom: 4 }}>Champion</span>}
                  <div style={{ fontSize: 12, color: 'var(--color-muted)' }}>
                    Acc: <strong>{m.accuracy_mean != null ? `${(m.accuracy_mean * 100).toFixed(1)}%` : '—'}</strong>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Recent Outcomes — Phase 9: prediction_store VERIFIED, real data */}
        <div className="glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>Recent Outcomes</h3>
            <a href="/shadow" style={{ fontSize: 12, color: '#3b5bdb', textDecoration: 'none' }}>View all →</a>
          </div>
          {sl ? <TableSkeleton rows={5} /> : (
            recent.map((p, i) => {
              const predWinner  = p.predicted_winner || '—'
              const actualWinner = p.actual_winner || null
              // Phase 5: Wrong badge ONLY when actual_winner is known
              const isCorrect = actualWinner != null ? p.is_correct : null
              const matchTitle = p.event_id || `${p.team_a || '?'} vs ${p.team_b || '?'}`
              const probVal = p.probability != null ? `${(p.probability * 100).toFixed(0)}%` : null

              return (
                <div key={i} style={{ padding: '10px 0', borderBottom: '1px solid var(--color-border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text)' }}>{matchTitle}</div>
                      <div style={{ fontSize: 11, color: '#475569', marginTop: 2 }}>
                        Predicted: <strong style={{ color: '#3b5bdb' }}>{predWinner}</strong>
                        {actualWinner && <span> | Actual: <strong>{actualWinner}</strong></span>}
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--color-muted)', marginTop: 2 }}>
                        {probVal && <span>Prob: <strong>{probVal}</strong> · </span>}
                        Model: <strong>{p.model_version ? p.model_version.slice(0, 20) + '…' : 'Champion'}</strong>
                        {p.prediction_timestamp && <span> · {fmtDateTime(p.prediction_timestamp)}</span>}
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {isCorrect === true && <span className="badge badge-success">✓ Correct</span>}
                      {isCorrect === false && <span className="badge badge-danger">✗ Wrong</span>}
                      {isCorrect === null && <span className="badge badge-warn">Pending</span>}
                    </div>
                  </div>
                </div>
              )
            })
          )}
          {!sl && recent.length === 0 && (
            <div style={{ color: 'var(--color-muted)', fontSize: 13, textAlign: 'center', padding: '20px 0' }}>
              No verified outcomes yet.
            </div>
          )}
        </div>
      </div>

      {/* System Metadata Footer — from dashboard_summary view */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginTop: 24 }}>
        {[
          { label: 'Champion Version',      val: metrics?.champion         || '—' },
          { label: 'Previous Champion',     val: metrics?.previous_champion || '—' },
          { label: 'Dataset Version',       val: metrics?.dataset_version   || '—' },
          { label: 'Drift %',               val: metrics?.drift_percentage != null ? `${metrics.drift_percentage}%` : '—' },
          { label: 'Confidence Calibration',val: metrics?.confidence_calibration != null ? `${(metrics.confidence_calibration * 100).toFixed(1)}%` : '—' },
          { label: 'Total Predictions',     val: metrics?.live_predictions != null ? metrics.live_predictions.toLocaleString() : '—' },
          { label: 'Last Updated',          val: metrics?.last_update ? fmtDateTime(metrics.last_update) : '—' },
        ].map(({ label, val }) => (
          <div key={label} className="glass-card" style={{ padding: '12px 16px' }}>
            <div style={{ fontSize: 11, color: 'var(--color-muted)', marginBottom: 4 }}>{label}</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text)', wordBreak: 'break-all' }}>{val}</div>
          </div>
        ))}
      </div>
    </DashboardLayout>
  )
}
