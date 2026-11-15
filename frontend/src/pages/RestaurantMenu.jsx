import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api/client';
import { useFetch } from '../hooks/useFetch';
import { useCart } from '../context/CartContext';
import { EmptyState, ErrorMessage, Loader, Pagination } from '../components/ui';
import { formatDateTime, formatMoney } from '../utils/format';

const PAGE_SIZE = 12;

export default function RestaurantMenu() {
  const { id } = useParams();
  const { items: cartItems, restaurant: cartRestaurant, addItem, setQuantity, count, total } = useCart();

  const [q, setQ] = useState('');
  const [debouncedQ, setDebouncedQ] = useState('');
  const [minPrice, setMinPrice] = useState('');
  const [maxPrice, setMaxPrice] = useState('');
  const [page, setPage] = useState(1);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQ(q.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [q]);

  const restaurant = useFetch(() => api.get(`/restaurants/${id}`), [id]);
  const menu = useFetch(
    () => api.get(`/restaurants/${id}/menu`, { q: debouncedQ, min_price: minPrice, max_price: maxPrice, page, page_size: PAGE_SIZE }),
    [id, debouncedQ, minPrice, maxPrice, page],
  );
  const reviews = useFetch(() => api.get(`/restaurants/${id}/reviews`, { page_size: 5 }), [id]);

  const quantityInCart = (dishId) => cartItems.find((i) => i.menu_item_id === dishId)?.quantity || 0;
  const r = restaurant.data;
  const cartHere = cartRestaurant?.id === Number(id) ? count : 0;

  if (restaurant.loading) return <Loader />;
  if (restaurant.error) {
    return (
      <>
        <ErrorMessage message={restaurant.error} />
        <Link to="/">&larr; Back to restaurants</Link>
      </>
    );
  }

  return (
    <section>
      <Link to="/" className="back-link">
        &larr; All restaurants
      </Link>
      <div className="card restaurant-header">
        <h1>{r.name}</h1>
        <p className="muted">{[r.cuisine, r.address].filter(Boolean).join(' · ')}</p>
        {r.description && <p>{r.description}</p>}
        <p className="rating">
          {r.avg_rating ? `★ ${r.avg_rating.toFixed(1)} (${r.review_count} reviews)` : 'No reviews yet'}
        </p>
      </div>

      <form className="filters" onSubmit={(e) => e.preventDefault()}>
        <label>
          Search dishes
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. dosa" />
        </label>
        <label>
          Min price
          <input type="number" min="0" value={minPrice} onChange={(e) => { setMinPrice(e.target.value); setPage(1); }} />
        </label>
        <label>
          Max price
          <input type="number" min="0" value={maxPrice} onChange={(e) => { setMaxPrice(e.target.value); setPage(1); }} />
        </label>
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => {
            setQ('');
            setMinPrice('');
            setMaxPrice('');
          }}
        >
          Clear
        </button>
      </form>

      <ErrorMessage message={menu.error} onRetry={() => menu.reload(false)} />
      {menu.loading && !menu.data && <Loader label="Loading menu..." />}
      {menu.data && menu.data.items.length === 0 && <EmptyState title="No dishes match your filters" />}

      <div className="grid">
        {menu.data?.items.map((dish) => {
          const qty = quantityInCart(dish.id);
          const inThisCart = cartRestaurant?.id === Number(id) && qty > 0;
          return (
            <article key={dish.id} className={`card dish-card ${dish.is_available ? '' : 'unavailable'}`}>
              <div>
                <h3>{dish.name}</h3>
                {dish.category && <p className="muted small">{dish.category}</p>}
                {dish.description && <p className="small">{dish.description}</p>}
              </div>
              <div className="dish-footer">
                <strong>{formatMoney(dish.price)}</strong>
                {!dish.is_available ? (
                  <span className="pill pill-ret-rejected">Unavailable</span>
                ) : inThisCart ? (
                  <div className="stepper" aria-label={`Quantity of ${dish.name}`}>
                    <button type="button" onClick={() => setQuantity(dish.id, qty - 1)} aria-label="Decrease">
                      &minus;
                    </button>
                    <span>{qty}</span>
                    <button type="button" onClick={() => setQuantity(dish.id, qty + 1)} aria-label="Increase">
                      +
                    </button>
                  </div>
                ) : (
                  <button type="button" className="btn btn-small" onClick={() => addItem(dish, r)}>
                    Add
                  </button>
                )}
              </div>
            </article>
          );
        })}
      </div>
      {menu.data && <Pagination page={menu.data.page} pageSize={menu.data.page_size} total={menu.data.total} onChange={setPage} />}

      <h2>Reviews</h2>
      {reviews.loading && <Loader label="Loading reviews..." />}
      {reviews.data?.items.length === 0 && <p className="muted">No reviews yet - be the first after your order arrives!</p>}
      <ul className="reviews">
        {reviews.data?.items.map((rev) => (
          <li key={rev.id} className="card">
            <strong>{'★'.repeat(rev.rating)}{'☆'.repeat(5 - rev.rating)}</strong>{' '}
            <span className="muted small">
              {rev.customer?.name} &middot; {formatDateTime(rev.created_at)}
            </span>
            {rev.comment && <p>{rev.comment}</p>}
          </li>
        ))}
      </ul>

      {cartHere > 0 && (
        <Link to="/cart" className="cart-bar">
          <span>
            {cartHere} item{cartHere > 1 ? 's' : ''} in cart
          </span>
          <strong>View cart &middot; {formatMoney(total)}</strong>
        </Link>
      )}
    </section>
  );
}
