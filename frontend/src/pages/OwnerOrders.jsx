import { useState } from 'react';
import { api } from '../api/client';
import { useAction, useFetch } from '../hooks/useFetch';
import OrderCard from '../components/OrderCard';
import ReturnActions from '../components/ReturnActions';
import { EMPTY_FILTERS, EmptyState, ErrorMessage, Loader, OrderFilters, Pagination } from '../components/ui';

const PAGE_SIZE = 6;
const NEXT_STEP = {
  PLACED: { status: 'ACCEPTED', label: 'Accept order' },
  ACCEPTED: { status: 'PREPARING', label: 'Start preparing' },
  PREPARING: { status: 'READY', label: 'Mark ready' },
};

function AssignControl({ order, partners, onDone }) {
  const [partnerId, setPartnerId] = useState('');
  const { busy, error, run } = useAction();

  async function assign() {
    const result = await run(() => api.post(`/owner/orders/${order.id}/assign`, { delivery_partner_id: Number(partnerId) }));
    if (result) onDone();
  }

  return (
    <div className="assign">
      <ErrorMessage message={error} />
      <select value={partnerId} onChange={(e) => setPartnerId(e.target.value)} aria-label={`Delivery partner for order ${order.id}`}>
        <option value="">Choose delivery partner...</option>
        {partners.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
            {p.phone ? ` (${p.phone})` : ''}
          </option>
        ))}
      </select>
      <button type="button" className="btn btn-small" disabled={!partnerId || busy} onClick={assign}>
        {busy ? 'Assigning...' : 'Assign'}
      </button>
    </div>
  );
}

export default function OwnerOrders() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const statusAction = useAction();

  const { data, loading, error, reload } = useFetch(
    () =>
      api.get('/owner/orders', {
        status: filters.status,
        date_from: filters.dateFrom,
        date_to: filters.dateTo,
        page,
        page_size: PAGE_SIZE,
      }),
    [filters, page],
    { pollMs: 20000 },
  );
  const partners = useFetch(() => api.get('/owner/delivery-partners'), []);

  const changeFilters = (next) => {
    setFilters(next);
    setPage(1);
  };

  async function advance(order, status) {
    const result = await statusAction.run(() => api.patch(`/owner/orders/${order.id}/status`, { status }));
    if (result) reload(true);
  }

  return (
    <section>
      <div className="page-head">
        <h1>Orders</h1>
      </div>
      <OrderFilters filters={filters} onChange={changeFilters} />

      <ErrorMessage message={statusAction.error} />
      <ErrorMessage message={error} onRetry={() => reload(false)} />
      {loading && !data && <Loader label="Loading orders..." />}
      {data && data.items.length === 0 && <EmptyState title="No orders match these filters" />}

      <div className="stack">
        {data?.items.map((order) => {
          const next = NEXT_STEP[order.status];
          return (
            <OrderCard key={order.id} order={order} perspective="owner">
              {next && (
                <button type="button" className="btn btn-small" disabled={statusAction.busy} onClick={() => advance(order, next.status)}>
                  {next.label}
                </button>
              )}
              {order.status === 'READY' && (
                <AssignControl order={order} partners={partners.data || []} onDone={() => reload(true)} />
              )}
              {order.return_status === 'requested' && <ReturnActions order={order} onDone={() => reload(true)} />}
            </OrderCard>
          );
        })}
      </div>

      {data && <Pagination page={data.page} pageSize={data.page_size} total={data.total} onChange={setPage} />}
    </section>
  );
}
