import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { useAction } from '../hooks/useFetch';
import { EmptyState, ErrorMessage } from '../components/ui';
import { formatMoney } from '../utils/format';

export default function Cart() {
  const { user } = useAuth();
  const { items, restaurant, total, setQuantity, removeItem, clearCart } = useCart();
  const navigate = useNavigate();
  const [address, setAddress] = useState(user?.address || '');
  const [notes, setNotes] = useState('');
  const { busy, error, run } = useAction();

  if (items.length === 0) {
    return (
      <EmptyState title="Your cart is empty">
        <Link to="/">Browse restaurants</Link> and add something tasty.
      </EmptyState>
    );
  }

  async function placeOrder(event) {
    event.preventDefault();
    const order = await run(() =>
      api.post('/orders', {
        items: items.map((i) => ({ menu_item_id: i.menu_item_id, quantity: i.quantity })),
        delivery_address: address.trim(),
        notes: notes.trim() || null,
      }),
    );
    if (order) {
      clearCart();
      navigate('/orders', { state: { placed: order.id } });
    }
  }

  return (
    <section className="narrow">
      <h1>Your cart</h1>
      <p className="muted">
        From <strong>{restaurant?.name}</strong>
      </p>

      <ul className="card cart-list">
        {items.map((item) => (
          <li key={item.menu_item_id}>
            <div>
              <strong>{item.name}</strong>
              <div className="muted small">{formatMoney(item.price)} each</div>
            </div>
            <div className="cart-controls">
              <div className="stepper">
                <button type="button" onClick={() => setQuantity(item.menu_item_id, item.quantity - 1)} aria-label={`Decrease ${item.name}`}>
                  &minus;
                </button>
                <span>{item.quantity}</span>
                <button type="button" onClick={() => setQuantity(item.menu_item_id, item.quantity + 1)} aria-label={`Increase ${item.name}`}>
                  +
                </button>
              </div>
              <strong className="line-total">{formatMoney(item.price * item.quantity)}</strong>
              <button type="button" className="btn btn-small btn-danger" onClick={() => removeItem(item.menu_item_id)}>
                Remove
              </button>
            </div>
          </li>
        ))}
        <li className="total">
          <span>Total</span>
          <strong>{formatMoney(total)}</strong>
        </li>
      </ul>

      <form className="card checkout" onSubmit={placeOrder}>
        <h2>Checkout</h2>
        <ErrorMessage message={error} />
        <label>
          Delivery address
          <textarea
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            required
            minLength={5}
            maxLength={500}
            rows={2}
            placeholder="Hostel, room number, landmark..."
          />
        </label>
        <label>
          Notes for the restaurant <small className="muted">(optional)</small>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={500} rows={2} />
        </label>
        <p className="notice">
          <strong>Dummy payment:</strong> no real money is charged. Your order is marked <code>mock_paid</code> as soon as it is
          placed.
        </p>
        <div className="row">
          <button type="button" className="btn btn-ghost" onClick={clearCart} disabled={busy}>
            Empty cart
          </button>
          <button type="submit" className="btn" disabled={busy}>
            {busy ? 'Placing order...' : `Pay ${formatMoney(total)} (dummy) & place order`}
          </button>
        </div>
      </form>
    </section>
  );
}
