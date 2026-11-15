import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useFetch } from '../hooks/useFetch';
import OrderCard from '../components/OrderCard';
import ReturnActions from '../components/ReturnActions';
import { EmptyState, ErrorMessage, Loader } from '../components/ui';
import { STATUS_LABELS } from '../utils/constants';
import { formatDateTime, formatMoney } from '../utils/format';

function Stat({ label, value, tone }) {
  return (
    <div className={`card stat ${tone || ''}`}>
      <span className="muted small">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default function OwnerDashboard() {
  const restaurant = useFetch(() => api.get('/owner/restaurant'), []);
  const stats = useFetch(() => api.get('/owner/stats'), [], { pollMs: 30000 });
  const reminders = useFetch(() => api.get('/owner/reminders'), [], { pollMs: 30000 });
  const returns = useFetch(() => api.get('/owner/returns', { return_status: 'requested', page_size: 5 }), [], { pollMs: 30000 });

  const s = stats.data;
  const refreshAll = () => {
    stats.reload(true);
    reminders.reload(true);
    returns.reload(true);
  };

  return (
    <section>
      <div className="page-head">
        <h1>{restaurant.data ? `${restaurant.data.name} - dashboard` : 'Restaurant dashboard'}</h1>
        <div className="row">
          <Link className="btn" to="/owner/orders">
            Manage orders
          </Link>
          <Link className="btn btn-ghost" to="/owner/menu">
            Manage menu
          </Link>
        </div>
      </div>

      <ErrorMessage message={restaurant.error || stats.error} onRetry={() => { restaurant.reload(false); stats.reload(false); }} />
      {stats.loading && !s && <Loader label="Loading statistics..." />}

      {s && (
        <>
          <div className="stats-grid">
            <Stat label="Total orders" value={s.total_orders} />
            <Stat label="Orders today" value={s.orders_today} />
            <Stat label="Delivered revenue" value={formatMoney(s.delivered_revenue)} />
            <Stat label="Avg. order value" value={formatMoney(s.average_order_value)} />
            <Stat label="Average rating" value={s.average_rating ? `★ ${s.average_rating.toFixed(1)} (${s.review_count})` : 'No reviews'} />
            <Stat label="Pending returns" value={s.pending_returns} tone={s.pending_returns ? 'warn' : ''} />
            <Stat label="Open reminders" value={s.open_reminders} tone={s.open_reminders ? 'warn' : ''} />
          </div>

          <div className="two-col">
            <div className="card">
              <h2>Orders by status</h2>
              {Object.keys(s.orders_by_status).length === 0 ? (
                <p className="muted">No orders yet.</p>
              ) : (
                <ul className="plain-list">
                  {Object.entries(s.orders_by_status).map(([status, count]) => (
                    <li key={status}>
                      <span>{STATUS_LABELS[status] || status}</span>
                      <strong>{count}</strong>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="card">
              <h2>Top dishes</h2>
              {s.top_items.length === 0 ? (
                <p className="muted">Nothing ordered yet.</p>
              ) : (
                <ol className="plain-list">
                  {s.top_items.map((item) => (
                    <li key={item.name}>
                      <span>{item.name}</span>
                      <strong>{item.quantity} sold</strong>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </div>
        </>
      )}

      <h2>Reminders</h2>
      <p className="muted small">Orders that have been sitting in PLACED or ACCEPTED for too long.</p>
      <ErrorMessage message={reminders.error} />
      {reminders.data?.length === 0 && <EmptyState title="All caught up">No stale orders right now.</EmptyState>}
      <ul className="reminders">
        {reminders.data?.map((r) => (
          <li key={r.id} className="alert alert-warn">
            <span>
              <strong>#{r.order_id}</strong> {r.message}
              <small className="muted"> &middot; {formatDateTime(r.created_at)}</small>
            </span>
            <Link className="btn btn-small" to="/owner/orders">
              Open orders
            </Link>
          </li>
        ))}
      </ul>

      <h2>Return &amp; refund requests</h2>
      <ErrorMessage message={returns.error} />
      {returns.data?.items.length === 0 && <EmptyState title="No pending return requests" />}
      <div className="stack">
        {returns.data?.items.map((order) => (
          <OrderCard key={order.id} order={order} perspective="owner">
            <ReturnActions order={order} onDone={refreshAll} />
          </OrderCard>
        ))}
      </div>
      {returns.data && returns.data.total > returns.data.items.length && (
        <p className="muted">
          Showing {returns.data.items.length} of {returns.data.total}. Approve or reject these to see more.
        </p>
      )}
    </section>
  );
}
