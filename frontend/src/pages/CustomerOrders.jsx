import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api } from '../api/client';
import { useAction, useFetch } from '../hooks/useFetch';
import OrderCard from '../components/OrderCard';
import { EMPTY_FILTERS, EmptyState, ErrorMessage, Loader, OrderFilters, Pagination, SuccessMessage } from '../components/ui';

const PAGE_SIZE = 5;

function ReviewForm({ order, onDone, onCancel }) {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState('');
  const { busy, error, run } = useAction();

  async function submit(e) {
    e.preventDefault();
    const result = await run(() => api.post(`/orders/${order.id}/review`, { rating, comment: comment.trim() || null }));
    if (result) onDone('Thanks for your review!');
  }

  return (
    <form className="inline-form" onSubmit={submit}>
      <ErrorMessage message={error} />
      <label>
        Rating
        <select value={rating} onChange={(e) => setRating(Number(e.target.value))}>
          {[5, 4, 3, 2, 1].map((n) => (
            <option key={n} value={n}>
              {'★'.repeat(n)} ({n})
            </option>
          ))}
        </select>
      </label>
      <label>
        Comment <small className="muted">(optional)</small>
        <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={2} maxLength={1000} />
      </label>
      <div className="row">
        <button type="button" className="btn btn-small btn-ghost" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="btn btn-small" disabled={busy}>
          {busy ? 'Submitting...' : 'Submit review'}
        </button>
      </div>
    </form>
  );
}

function ReturnForm({ order, onDone, onCancel }) {
  const [reason, setReason] = useState('');
  const { busy, error, run } = useAction();

  async function submit(e) {
    e.preventDefault();
    const result = await run(() => api.post(`/orders/${order.id}/return`, { reason: reason.trim() }));
    if (result) onDone('Return request sent to the restaurant.');
  }

  return (
    <form className="inline-form" onSubmit={submit}>
      <ErrorMessage message={error} />
      <label>
        Why are you returning this order?
        <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={2} required minLength={5} maxLength={500} />
      </label>
      <div className="row">
        <button type="button" className="btn btn-small btn-ghost" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="btn btn-small" disabled={busy}>
          {busy ? 'Sending...' : 'Request return / refund'}
        </button>
      </div>
    </form>
  );
}

export default function CustomerOrders() {
  const location = useLocation();
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [openForm, setOpenForm] = useState(null); // { id, type: 'review' | 'return' }
  const [notice, setNotice] = useState(location.state?.placed ? `Order #${location.state.placed} placed! (dummy payment recorded)` : '');
  const cancelAction = useAction();

  const { data, loading, error, reload } = useFetch(
    () =>
      api.get('/orders', {
        status: filters.status,
        date_from: filters.dateFrom,
        date_to: filters.dateTo,
        page,
        page_size: PAGE_SIZE,
      }),
    [filters, page],
    { pollMs: 20000 }, // keeps the tracking status fresh
  );

  const changeFilters = (next) => {
    setFilters(next);
    setPage(1);
  };

  const finish = (message) => {
    setOpenForm(null);
    setNotice(message);
    reload(true);
  };

  async function cancel(order) {
    if (!window.confirm(`Cancel order #${order.id}?`)) return;
    const result = await cancelAction.run(() => api.post(`/orders/${order.id}/cancel`));
    if (result) finish(`Order #${order.id} was cancelled.`);
  }

  return (
    <section>
      <div className="page-head">
        <h1>My orders</h1>
        <Link className="btn btn-ghost" to="/insights">
          Ask AI about my orders
        </Link>
      </div>

      <SuccessMessage message={notice} />
      <ErrorMessage message={cancelAction.error} />
      <OrderFilters filters={filters} onChange={changeFilters} />

      <ErrorMessage message={error} onRetry={() => reload(false)} />
      {loading && !data && <Loader label="Loading your orders..." />}
      {data && data.items.length === 0 && (
        <EmptyState title="No orders found">
          {filters.status || filters.dateFrom || filters.dateTo ? 'Try clearing the filters.' : <Link to="/">Order something tasty</Link>}
        </EmptyState>
      )}

      <div className="stack">
        {data?.items.map((order) => {
          const canReview = order.status === 'DELIVERED' && !order.review;
          const canReturn = order.status === 'DELIVERED' && order.return_status === 'none';
          return (
            <OrderCard key={order.id} order={order} perspective="customer" showTracker>
              {order.status === 'PLACED' && (
                <button type="button" className="btn btn-small btn-danger" onClick={() => cancel(order)} disabled={cancelAction.busy}>
                  Cancel order
                </button>
              )}
              {canReview && openForm?.id !== order.id && (
                <button type="button" className="btn btn-small" onClick={() => setOpenForm({ id: order.id, type: 'review' })}>
                  Rate &amp; review
                </button>
              )}
              {canReturn && openForm?.id !== order.id && (
                <button type="button" className="btn btn-small btn-ghost" onClick={() => setOpenForm({ id: order.id, type: 'return' })}>
                  Request return / refund
                </button>
              )}
              {openForm?.id === order.id && openForm.type === 'review' && (
                <ReviewForm order={order} onDone={finish} onCancel={() => setOpenForm(null)} />
              )}
              {openForm?.id === order.id && openForm.type === 'return' && (
                <ReturnForm order={order} onDone={finish} onCancel={() => setOpenForm(null)} />
              )}
            </OrderCard>
          );
        })}
      </div>

      {data && <Pagination page={data.page} pageSize={data.page_size} total={data.total} onChange={setPage} />}
    </section>
  );
}
