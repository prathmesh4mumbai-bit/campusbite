import { STATUS_LABELS, TRACK_STEPS, ORDER_STATUSES } from '../utils/constants';

export function Loader({ label = 'Loading...' }) {
  return (
    <div className="loader" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorMessage({ message, onRetry }) {
  if (!message) return null;
  return (
    <div className="alert alert-error" role="alert">
      <span>{message}</span>
      {onRetry && (
        <button type="button" className="btn btn-small btn-ghost" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function SuccessMessage({ message }) {
  if (!message) return null;
  return (
    <div className="alert alert-success" role="status">
      {message}
    </div>
  );
}

export function EmptyState({ title, children }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      {children && <p className="muted">{children}</p>}
    </div>
  );
}

export function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{STATUS_LABELS[status] || status}</span>;
}

export function Pagination({ page, pageSize, total, onChange }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (total <= pageSize) return null;
  return (
    <nav className="pagination" aria-label="Pagination">
      <button type="button" className="btn btn-small btn-ghost" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        &larr; Prev
      </button>
      <span className="muted">
        Page {page} of {pages} &middot; {total} total
      </span>
      <button
        type="button"
        className="btn btn-small btn-ghost"
        disabled={page >= pages}
        onClick={() => onChange(page + 1)}
      >
        Next &rarr;
      </button>
    </nav>
  );
}

export function OrderTracker({ status }) {
  if (status === 'CANCELLED' || status === 'REFUNDED') return null;
  const current = TRACK_STEPS.indexOf(status);
  return (
    <ol className="tracker" aria-label="Order progress">
      {TRACK_STEPS.map((step, index) => (
        <li key={step} className={index < current ? 'done' : index === current ? 'current' : ''}>
          <span className="dot" />
          <span className="tracker-label">{STATUS_LABELS[step]}</span>
        </li>
      ))}
    </ol>
  );
}

/** Status + date range filter shared by all order lists. `filters` = { status, dateFrom, dateTo } */
export function OrderFilters({ filters, onChange, statuses = ORDER_STATUSES, showDates = true }) {
  const set = (patch) => onChange({ ...filters, ...patch });
  return (
    <form className="filters" onSubmit={(e) => e.preventDefault()}>
      <label>
        Status
        <select value={filters.status} onChange={(e) => set({ status: e.target.value })}>
          <option value="">All</option>
          {statuses.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABELS[s] || s}
            </option>
          ))}
        </select>
      </label>
      {showDates && (
        <>
          <label>
            From
            <input type="date" value={filters.dateFrom} max={filters.dateTo || undefined} onChange={(e) => set({ dateFrom: e.target.value })} />
          </label>
          <label>
            To
            <input type="date" value={filters.dateTo} min={filters.dateFrom || undefined} onChange={(e) => set({ dateTo: e.target.value })} />
          </label>
        </>
      )}
      <button
        type="button"
        className="btn btn-ghost"
        onClick={() => onChange({ status: '', dateFrom: '', dateTo: '' })}
      >
        Reset
      </button>
    </form>
  );
}

export const EMPTY_FILTERS = { status: '', dateFrom: '', dateTo: '' };
