import EmptyState from './EmptyState'

// White card wrapper for a chart. The chart itself is passed as children.
function ChartCard({ title, subtitle, loading = false, empty = false, emptyText = 'No data to show yet.', children }) {
  return (
    <div data-testid="chart-card" className="bg-white rounded-xl border border-[#EEEEF2] shadow-sm p-5">
      <h3 className="text-base font-semibold text-[#14142B]">{title}</h3>
      {subtitle && <p className="text-sm text-[#71717A] mt-0.5">{subtitle}</p>}
      <div className="mt-4">
        {loading ? (
          <div data-testid="chart-card-loading" className="skeleton h-48 w-full rounded-lg" />
        ) : empty ? (
          <EmptyState title={emptyText} />
        ) : (
          children
        )}
      </div>
    </div>
  )
}

export default ChartCard
