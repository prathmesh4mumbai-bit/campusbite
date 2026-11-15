import { StatusBadge, OrderTracker } from './ui';
import { formatDateTime, formatMoney, titleCase } from '../utils/format';

/**
 * One order, rendered for a given point of view:
 *  - 'customer': shows the restaurant and the rider
 *  - 'owner':    shows the customer and the rider
 *  - 'delivery': shows pickup restaurant and the customer's delivery details
 * Action buttons / forms are passed in as children.
 */
export default function OrderCard({ order, perspective, showTracker = false, children }) {
  const returnActive = order.return_status !== 'none';
  return (
    <article className="card order-card">
      <header className="order-head">
        <div>
          <h3>Order #{order.id}</h3>
          <p className="muted small">{formatDateTime(order.created_at)}</p>
        </div>
        <StatusBadge status={order.status} />
      </header>

      <dl className="meta">
        {perspective !== 'owner' && (
          <div>
            <dt>{perspective === 'delivery' ? 'Pick up from' : 'Restaurant'}</dt>
            <dd>{order.restaurant.name}</dd>
          </div>
        )}
        {perspective !== 'customer' && (
          <div>
            <dt>Customer</dt>
            <dd>
              {order.customer.name}
              {order.customer.phone ? ` · ${order.customer.phone}` : ''}
            </dd>
          </div>
        )}
        <div>
          <dt>Deliver to</dt>
          <dd>{order.delivery_address}</dd>
        </div>
        {order.notes && (
          <div>
            <dt>Notes</dt>
            <dd>{order.notes}</dd>
          </div>
        )}
        {perspective !== 'delivery' && order.delivery_partner && (
          <div>
            <dt>Delivery partner</dt>
            <dd>
              {order.delivery_partner.name}
              {order.delivery_partner.phone ? ` · ${order.delivery_partner.phone}` : ''}
            </dd>
          </div>
        )}
      </dl>

      <ul className="items">
        {order.items.map((item) => (
          <li key={item.id}>
            <span>
              {item.quantity} &times; {item.name}
            </span>
            <span>{formatMoney(item.unit_price * item.quantity)}</span>
          </li>
        ))}
        <li className="total">
          <span>Total</span>
          <span>{formatMoney(order.total_amount)}</span>
        </li>
      </ul>

      <div className="pills">
        <span className={`pill pill-pay-${order.payment_status}`}>Payment: {titleCase(order.payment_status)}</span>
        {returnActive && <span className={`pill pill-ret-${order.return_status}`}>Return: {titleCase(order.return_status)}</span>}
        {order.review && <span className="pill pill-review">{'★'.repeat(order.review.rating)} reviewed</span>}
      </div>

      {returnActive && order.return_reason && (
        <p className="small">
          <strong>Return reason:</strong> {order.return_reason}
        </p>
      )}
      {order.review?.comment && (
        <p className="small">
          <strong>Review:</strong> {order.review.comment}
        </p>
      )}

      {order.payments.length > 0 && (
        <details className="ledger">
          <summary>Payment records ({order.payments.length})</summary>
          <ul>
            {order.payments.map((p) => (
              <li key={p.id}>
                {titleCase(p.entry_type)} &middot; {formatMoney(p.amount)} &middot; {p.reference} &middot;{' '}
                {formatDateTime(p.created_at)}
              </li>
            ))}
          </ul>
        </details>
      )}

      {showTracker && <OrderTracker status={order.status} />}
      {children && <div className="actions">{children}</div>}
    </article>
  );
}
