export function Skeleton({ className = '', style = {} }) {
  return <div className={`skeleton ${className}`} style={{ height: 16, ...style }} />
}

export function CardSkeleton() {
  return (
    <div className="card space-y-3">
      <Skeleton style={{ width: '40%', height: 12 }} />
      <Skeleton style={{ width: '70%', height: 28 }} />
      <Skeleton style={{ width: '50%', height: 12 }} />
    </div>
  )
}

export function TableSkeleton({ rows = 5 }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} style={{ height: 36, borderRadius: 8 }} />
      ))}
    </div>
  )
}
