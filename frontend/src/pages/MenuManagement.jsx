import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAction, useFetch } from '../hooks/useFetch';
import { EmptyState, ErrorMessage, Loader, Pagination, SuccessMessage } from '../components/ui';
import { formatMoney } from '../utils/format';

const PAGE_SIZE = 8;
const BLANK = { name: '', category: '', price: '', description: '', is_available: true };

function DishForm({ editing, onSaved, onCancel }) {
  const [form, setForm] = useState(BLANK);
  const { busy, error, setError, run } = useAction();

  // Load the dish into the form when "Edit" is clicked.
  useEffect(() => {
    setError('');
    setForm(
      editing
        ? {
            name: editing.name,
            category: editing.category || '',
            price: String(editing.price),
            description: editing.description || '',
            is_available: editing.is_available,
          }
        : BLANK,
    );
  }, [editing, setError]);

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));

  async function submit(e) {
    e.preventDefault();
    const payload = {
      name: form.name.trim(),
      category: form.category.trim() || null,
      description: form.description.trim() || null,
      price: Number(form.price),
      is_available: form.is_available,
    };
    const saved = await run(() => (editing ? api.put(`/owner/menu/${editing.id}`, payload) : api.post('/owner/menu', payload)));
    if (saved) {
      setForm(BLANK);
      onSaved(editing ? `Updated "${saved.name}".` : `Added "${saved.name}" to your menu.`);
    }
  }

  return (
    <form className="card dish-form" onSubmit={submit}>
      <h2>{editing ? `Edit "${editing.name}"` : 'Add a new dish'}</h2>
      <ErrorMessage message={error} />
      <label>
        Name
        <input value={form.name} onChange={set('name')} required maxLength={150} />
      </label>
      <div className="two-col tight">
        <label>
          Price (&#8377;)
          <input type="number" min="0.01" max="100000" step="0.01" value={form.price} onChange={set('price')} required />
        </label>
        <label>
          Category
          <input value={form.category} onChange={set('category')} maxLength={80} placeholder="e.g. Main Course" />
        </label>
      </div>
      <label>
        Description
        <textarea rows={2} value={form.description} onChange={set('description')} maxLength={1000} />
      </label>
      <label className="check">
        <input type="checkbox" checked={form.is_available} onChange={set('is_available')} />
        Available to order
      </label>
      <div className="row">
        {editing && (
          <button type="button" className="btn btn-ghost" onClick={onCancel}>
            Cancel edit
          </button>
        )}
        <button type="submit" className="btn" disabled={busy}>
          {busy ? 'Saving...' : editing ? 'Save changes' : 'Add dish'}
        </button>
      </div>
    </form>
  );
}

export default function MenuManagement() {
  const [q, setQ] = useState('');
  const [debouncedQ, setDebouncedQ] = useState('');
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState(null);
  const [notice, setNotice] = useState('');
  const rowAction = useAction();

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQ(q.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [q]);

  const { data, loading, error, reload } = useFetch(
    () => api.get('/owner/menu', { q: debouncedQ, page, page_size: PAGE_SIZE }),
    [debouncedQ, page],
  );

  async function toggle(dish) {
    const result = await rowAction.run(() => api.patch(`/owner/menu/${dish.id}/availability`, { is_available: !dish.is_available }));
    if (result) reload(true);
  }

  async function remove(dish) {
    if (!window.confirm(`Delete "${dish.name}"? Past orders keep their record of it.`)) return;
    const result = await rowAction.run(() => api.delete(`/owner/menu/${dish.id}`));
    if (result !== undefined) {
      if (editing?.id === dish.id) setEditing(null);
      setNotice(`Deleted "${dish.name}".`);
      reload(true);
    }
  }

  return (
    <section>
      <div className="page-head">
        <h1>Menu management</h1>
        <input type="search" className="search" placeholder="Search your dishes..." value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search dishes" />
      </div>

      <div className="menu-layout">
        <DishForm
          editing={editing}
          onCancel={() => setEditing(null)}
          onSaved={(message) => {
            setEditing(null);
            setNotice(message);
            reload(true);
          }}
        />

        <div>
          <SuccessMessage message={notice} />
          <ErrorMessage message={rowAction.error} />
          <ErrorMessage message={error} onRetry={() => reload(false)} />
          {loading && !data && <Loader label="Loading menu..." />}
          {data && data.items.length === 0 && <EmptyState title="No dishes yet">Use the form to add your first dish.</EmptyState>}

          <ul className="stack tight">
            {data?.items.map((dish) => (
              <li key={dish.id} className={`card menu-row ${dish.is_available ? '' : 'unavailable'}`}>
                <div>
                  <strong>{dish.name}</strong> <span className="muted">&middot; {formatMoney(dish.price)}</span>
                  <div className="muted small">{dish.category || 'Uncategorised'}</div>
                </div>
                <div className="row">
                  <label className="switch" title="Toggle availability">
                    <input type="checkbox" checked={dish.is_available} disabled={rowAction.busy} onChange={() => toggle(dish)} />
                    <span>{dish.is_available ? 'Available' : 'Unavailable'}</span>
                  </label>
                  <button type="button" className="btn btn-small btn-ghost" onClick={() => setEditing(dish)}>
                    Edit
                  </button>
                  <button type="button" className="btn btn-small btn-danger" onClick={() => remove(dish)} disabled={rowAction.busy}>
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
          {data && <Pagination page={data.page} pageSize={data.page_size} total={data.total} onChange={setPage} />}
        </div>
      </div>
    </section>
  );
}
