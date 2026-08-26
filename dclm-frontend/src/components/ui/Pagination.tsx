interface PaginationProps {
  page: number;
  totalPages: number;
  totalCount: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, totalPages, totalCount, pageSize, onPageChange }: PaginationProps) {
  if (totalCount === 0) return null;
  const startIdx = (page - 1) * pageSize;
  const endIdx = Math.min(startIdx + pageSize, totalCount);

  return (
    <div className="list-pagination">
      <span className="muted" style={{ fontSize: '.82rem' }}>
        Showing {startIdx + 1}–{endIdx} of {totalCount}
      </span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <button className="btn sm outline" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          Prev
        </button>
        <span className="muted" style={{ fontSize: '.82rem' }}>
          Page {page} of {totalPages}
        </span>
        <button className="btn sm outline" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
          Next
        </button>
      </div>
    </div>
  );
}
