import { ChevronLeft, ChevronRight } from 'lucide-react'

// Page controls for a server-paginated list.
// onChange(newPage) is called when Previous / Next is clicked.
function Pagination({ page, totalPages, count, pageSize, onChange }) {
  if (totalPages <= 1) return null
  const from = (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, count)
  const btn =
    'flex items-center gap-1 px-3 py-1.5 rounded-lg border border-[#EEEEF2] bg-white text-sm text-[#14142B] hover:bg-[#EDE9FE] transition disabled:opacity-40 disabled:hover:bg-white disabled:cursor-not-allowed'

  return (
    <div data-testid="pagination" className="flex items-center justify-between mt-4">
      <p data-testid="pagination-info" className="text-sm text-[#71717A]">
        Showing {from}–{to} of {count}
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          data-testid="pagination-prev"
          className={btn}
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
        >
          <ChevronLeft size={16} /> Previous
        </button>
        <span data-testid="pagination-page" className="text-sm text-[#71717A]">
          Page {page} of {totalPages}
        </span>
        <button
          type="button"
          data-testid="pagination-next"
          className={btn}
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
        >
          Next <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )
}

export default Pagination
