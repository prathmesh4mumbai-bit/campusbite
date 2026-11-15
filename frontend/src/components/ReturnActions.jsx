import { api } from '../api/client';
import { useAction } from '../hooks/useFetch';
import { ErrorMessage } from './ui';

/** Approve / reject buttons for a pending return request (restaurant owner). */
export default function ReturnActions({ order, onDone }) {
  const { busy, error, run } = useAction();

  const decide = async (decision) => {
    if (decision === 'approve' && !window.confirm(`Approve the return and refund for order #${order.id}?`)) return;
    const result = await run(() => api.post(`/owner/orders/${order.id}/return/${decision}`));
    if (result) onDone?.();
  };

  return (
    <>
      <ErrorMessage message={error} />
      <button type="button" className="btn btn-small" disabled={busy} onClick={() => decide('approve')}>
        Approve &amp; refund
      </button>
      <button type="button" className="btn btn-small btn-danger" disabled={busy} onClick={() => decide('reject')}>
        Reject return
      </button>
    </>
  );
}
