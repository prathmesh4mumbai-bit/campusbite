import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { useFetch } from '../hooks/useFetch';
import { EmptyState, ErrorMessage, Loader, Pagination } from '../components/ui';

const PAGE_SIZE = 9;

export default function Restaurants() {
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [page, setPage] = useState(1);

  // Wait for the user to stop typing before hitting the API.
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebounced(search.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const { data, loading, error, reload } = useFetch(
    () => api.get('/restaurants', { search: debounced, page, page_size: PAGE_SIZE }),
    [debounced, page],
  );

  return (
    <section>
      <div className="page-head">
        <h1>Hungry? Pick a restaurant</h1>
        <input
          type="search"
          className="search"
          placeholder="Search by name or cuisine..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search restaurants"
        />
      </div>

      <ErrorMessage message={error} onRetry={() => reload(false)} />
      {loading && !data && <Loader label="Finding restaurants..." />}

      {data && data.items.length === 0 && <EmptyState title="No restaurants found">Try a different search.</EmptyState>}

      <div className="grid">
        {data?.items.map((r) => (
          <Link key={r.id} to={`/restaurants/${r.id}`} className="card restaurant-card">
            <div className="restaurant-banner" aria-hidden="true">
              {r.image_url ? <img src={r.image_url} alt="" /> : <span>{'🍽️'}</span>}
            </div>
            <h3>{r.name}</h3>
            <p className="muted small">{[r.cuisine, r.address].filter(Boolean).join(' · ')}</p>
            {r.description && <p className="small clamp">{r.description}</p>}
            <p className="rating">
              {r.avg_rating ? (
                <>
                  {'★'} {r.avg_rating.toFixed(1)} <span className="muted">({r.review_count})</span>
                </>
              ) : (
                <span className="muted">No reviews yet</span>
              )}
            </p>
          </Link>
        ))}
      </div>

      {data && <Pagination page={data.page} pageSize={data.page_size} total={data.total} onChange={setPage} />}
    </section>
  );
}
