import { useState } from 'react';
import { api } from '../api/client';
import { useAction, useFetch } from '../hooks/useFetch';
import OrderCard from '../components/OrderCard';
import { EmptyState, ErrorMessage, Loader, OrderFilters, Pagination } from '../components/ui';

const PAGE_SIZE = 6;
const ACTIVE_STATUSES = ['ASSIGNED', 'OUT_FOR_DELIVERY'];

export default function DeliveryDashboard() {
  const [tab, setTab] = useState('active');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const action = useAction();

  const { data, loading, error, reload } = useFetch(
    () =>
      tab === 'active'
        ? api.get('/delivery/orders', { status, page, page_size: PAGE_SIZE })
        : api.get('/delivery/history', { page, page_size: PAGE_SIZE }),
    [tab, status, page],
    { pollMs: 20000 },
  );

  const switchTab = (next) => {
    setTab(next);
    setStatus('');
    setPage(1);
  };

  async function update(order, nextStatus) {
    const result = await action.run(() => api.patch(`/delivery/orders/${order.id}/status`, { status: nextStatus }));
    if (result) reload(true);
  }

  return (
    <section>
      <div className="page-head">
        <h1>My deliveries</h1>
      </div>

      <div className="tabs" role="tablist">
        <button type="button" role="tab" aria-selected={tab === 'active'} className={tab === 'active' ? 'active' : ''} onClick={() => switchTab('active')}>
          Assigned to me
        </button>
        <button type="button" role="tab" aria-selected={tab === 'history'} className={tab === 'history' ? 'active' : ''} onClick={() => switchTab('history')}>
          Delivery history
        </button>
      </div>

      {tab === 'active' && (
        <OrderFilters
          filters={{ status, dateFrom: '', dateTo: '' }}
          onChange={(f) => {
            setStatus(f.status);
            setPage(1);
          }}
          statuses={ACTIVE_STATUSES}
          showDates={false}
        />
      )}

      <ErrorMessage message={action.error} />
      <ErrorMessage message={error} onRetry={() => reload(false)} />
      {loading && !data && <Loader label="Loading deliveries..." />}
      {data && data.items.length === 0 && (
        <EmptyState title={tab === 'active' ? 'No deliveries assigned right now' : 'No completed deliveries yet'}>
          {tab === 'active' ? 'New assignments from restaurants will show up here.' : ''}
        </EmptyState>
      )}

      <div className="stack">
        {data?.items.map((order) => (
          <OrderCard key={order.id} order={order} perspective="delivery">
            {order.status === 'ASSIGNED' && (
              <button type="button" className="btn btn-small" disabled={action.busy} onClick={() => update(order, 'OUT_FOR_DELIVERY')}>
                Pick up &amp; start delivery
              </button>
            )}
            {order.status === 'OUT_FOR_DELIVERY' && (
              <button type="button" className="btn btn-small" disabled={action.busy} onClick={() => update(order, 'DELIVERED')}>
                Mark as delivered
              </button>
            )}
          </OrderCard>
        ))}
      </div>

      {data && <Pagination page={data.page} pageSize={data.page_size} total={data.total} onChange={setPage} />}
    </section>
  );
}
