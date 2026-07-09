export function WakeupBanner() {
  return (
    <div className="wakeup-banner mb-6">
      <span className="spin" />
      <div>
        <div style={{ fontWeight: 600 }}>Waking up the Prediction Engine…</div>
        <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>
          The backend is starting up. This usually takes 15–30 seconds on the first request.
        </div>
      </div>
    </div>
  )
}

export function ErrorBanner({ message }) {
  return (
    <div style={{
      background: '#fff5f5', border: '1px solid #fecaca', borderRadius: 12,
      padding: '16px 20px', color: '#991b1b', fontSize: 13.5, marginBottom: 24
    }}>
      ⚠️ {message || 'Could not load data. Please try again later.'}
    </div>
  )
}
