# CampusBite - Restaurant Ordering & Delivery Platform

CampusBite is a full-stack food ordering and delivery app for a campus. **Customers** browse restaurants and order food, **restaurant owners** manage menus and orders, and **delivery partners** handle their assigned deliveries. Customers also get **AI-powered insights** about their own order history (OpenAI).

## Technologies

| Layer | Stack |
|---|---|
| Frontend | React 18, JavaScript (ES6+), React Hooks + Context, React Router DOM v6, Fetch API, Vite |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 ORM, JWT (PyJWT), bcrypt |
| Database | PostgreSQL 16 (SQLite supported for quick local runs) |
| AI | OpenAI API (Chat Completions, server-side only) |
| DevOps | Docker, Docker Compose, Git/GitHub |

## Features

**Customer** - register/login, browse restaurants, view menus, search dishes by name and filter by price, cart (add/update/remove), checkout with **dummy payment** (`mock_paid`), order history with status/date filters and pagination, live status tracker (auto-refreshes), cancel while `PLACED`, review after delivery, return/refund request after delivery (one per order, reason required), **AI order insights**.

**Restaurant owner** - add/edit/delete dishes, toggle availability, view incoming orders (status + date filters, pagination), accept and move orders through `PREPARING` -> `READY`, assign delivery partners to `READY` orders, approve/reject return requests (approval records a refund), restaurant statistics, **reminders** for orders left in `PLACED`/`ACCEPTED` for more than 15 minutes.

**Delivery partner** - sees only orders assigned to them with customer delivery details, moves them `ASSIGNED` -> `OUT_FOR_DELIVERY` -> `DELIVERED`, filters by status, views delivery history.

**Platform** - JWT auth + bcrypt hashing, role-based access control enforced **on the backend** (and mirrored by protected frontend routes), request logging + response-time middleware, background reminder job, pagination, validation and consistent HTTP status codes, responsive UI.

### Order lifecycle (enforced by the backend)

```
PLACED -> ACCEPTED -> PREPARING -> READY -> ASSIGNED -> OUT_FOR_DELIVERY -> DELIVERED -> (REFUNDED)
   \-> CANCELLED (customer, only while PLACED)
```

| Transition | Who |
|---|---|
| PLACED -> CANCELLED | the customer who owns the order |
| PLACED -> ACCEPTED -> PREPARING -> READY | owner of that restaurant |
| READY -> ASSIGNED (choose a delivery partner) | owner of that restaurant |
| ASSIGNED -> OUT_FOR_DELIVERY -> DELIVERED | the assigned delivery partner only |
| DELIVERED -> REFUNDED | owner approving a return request |

Anything else (skipping steps, going backwards, cancelling a delivered order, ...) is rejected with `400`/`403`. Other people's orders return `404`.

## Project structure

```
campusbite/
├── docker-compose.yml        # backend + PostgreSQL
├── .env.example              # variables for Docker Compose (copy to .env)
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example          # only for running without Docker
│   ├── app/
│   │   ├── main.py           # app, lifespan (DB init, seed, reminder job), CORS
│   │   ├── config.py         # settings from environment variables
│   │   ├── database.py       # engine / session
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic request/response models
│   │   ├── security.py       # bcrypt + JWT
│   │   ├── deps.py           # auth + role dependencies (RBAC)
│   │   ├── services.py       # order state machine, payments, pagination helpers
│   │   ├── middleware.py     # request logging + timing
│   │   ├── tasks.py          # background reminder job
│   │   ├── seed.py           # demo data
│   │   └── routers/          # auth, restaurants, orders, owner, delivery, ai
│   └── tests/                # end-to-end API tests (pytest)
└── frontend/
    ├── .env.example
    └── src/
        ├── api/              # fetch wrapper (JWT header, error handling)
        ├── context/          # AuthContext, CartContext
        ├── hooks/            # useFetch, useAction
        ├── components/       # Navbar, ProtectedRoute, OrderCard, ui.jsx ...
        └── pages/            # Login, Register, Restaurants, RestaurantMenu, Cart,
                              # CustomerOrders, AIInsights, OwnerDashboard,
                              # OwnerOrders, MenuManagement, DeliveryDashboard
```

## Environment variables

Docker Compose reads a `.env` file in the repository root. Copy the template and fill it in:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | **yes** | Password for the database user (use letters, digits, `-`, `_`) |
| `POSTGRES_USER` / `POSTGRES_DB` | no | Default `campusbite` |
| `JWT_SECRET` | **yes** | Signing key. Generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | Default `1440` (24h) |
| `OPENAI_API_KEY` | for AI | Without it the AI endpoint returns `503 not configured`; everything else works |
| `OPENAI_MODEL` | no | Default `gpt-4o-mini` |
| `AI_RATE_LIMIT_PER_MINUTE` | no | Per-user cap on AI requests, default `10` |
| `CORS_ORIGINS` | no | Comma-separated frontend origins, default `http://localhost:5173` |
| `REMINDER_THRESHOLD_MINUTES` | no | Default `15` |
| `REMINDER_INTERVAL_SECONDS` | no | How often the job scans, default `60` |
| `SEED_DEMO_DATA` / `SEED_DEMO_PASSWORD` | no | Demo accounts, see below |

The frontend has its own optional `frontend/.env` (see `frontend/.env.example`): `VITE_API_URL`, `VITE_SHOW_DEMO_LOGINS`, `VITE_DEMO_PASSWORD`.

> `.env` files are git-ignored. Secrets are never baked into the Docker image or committed.

## Run the backend with Docker Compose

```bash
cp .env.example .env          # then set POSTGRES_PASSWORD, JWT_SECRET (and OPENAI_API_KEY)
docker compose up --build
```

- API: http://localhost:8000 - interactive docs (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/health

Stop with `docker compose down` (add `-v` to also wipe the database volume).

## Run the frontend locally

Requires Node.js 18+.

```bash
cd frontend
cp .env.example .env          # optional; defaults point at http://localhost:8000
npm install
npm run dev                   # http://localhost:5173
```

Production build: `npm run build` (output in `frontend/dist`).

## Database setup

There is nothing to run by hand. On startup the backend waits for PostgreSQL, **creates all tables** from the SQLAlchemy models, and (when `SEED_DEMO_DATA=true` and the database is empty) inserts demo data.

Tables: `users`, `restaurants`, `menu_items`, `orders`, `order_items`, `reviews`, `payment_ledger`, `admin_reminder_logs`.

Relationships: a customer has many orders; a restaurant has many menu items and orders; an order has many order items, many payment-ledger entries and at most one review (unique constraint); a delivery partner can be assigned to many orders. Order items snapshot the dish name and price so history survives menu edits.

To use another database, set `DATABASE_URL` (any SQLAlchemy URL). To reset locally: `docker compose down -v`.

### Demo accounts

Created automatically when `SEED_DEMO_DATA=true`. Password is `SEED_DEMO_PASSWORD` (default `Demo@1234`). **Turn seeding off for any real deployment.**

| Role | Email |
|---|---|
| Customer | `customer@campusbite.dev` |
| Restaurant owner | `owner1@campusbite.dev` (Canteen Classics), `owner2@campusbite.dev` (Wrap & Roll), `owner3@campusbite.dev` (Southern Spice) |
| Delivery partner | `driver1@campusbite.dev`, `driver2@campusbite.dev` |

Anyone can also register as a customer, owner (creates a restaurant) or delivery partner on the sign-up page.

## API documentation

Swagger UI at `/docs`, ReDoc at `/redoc`. All protected endpoints take `Authorization: Bearer <token>`. List endpoints accept `page` (default 1) and `page_size` (default 10, max 50) and return `{ items, total, page, page_size }`.

| Area | Endpoint | Role |
|---|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` | public / any |
| Browse | `GET /restaurants?search=`, `GET /restaurants/{id}`, `GET /restaurants/{id}/menu?q=&min_price=&max_price=`, `GET /restaurants/{id}/reviews` | public |
| Customer orders | `POST /orders`, `GET /orders?status=&date_from=&date_to=`, `GET /orders/{id}` | customer (detail: any involved party) |
| | `POST /orders/{id}/cancel`, `POST /orders/{id}/review`, `POST /orders/{id}/return` | customer |
| Owner | `GET/PUT /owner/restaurant` | owner |
| | `GET/POST /owner/menu`, `PUT/DELETE /owner/menu/{id}`, `PATCH /owner/menu/{id}/availability` | owner |
| | `GET /owner/orders?status=&date_from=&date_to=`, `PATCH /owner/orders/{id}/status` | owner |
| | `GET /owner/delivery-partners`, `POST /owner/orders/{id}/assign` | owner |
| | `GET /owner/returns`, `POST /owner/orders/{id}/return/approve`, `.../reject` | owner |
| | `GET /owner/stats`, `GET /owner/reminders` | owner |
| Delivery | `GET /delivery/orders?status=`, `GET /delivery/history`, `PATCH /delivery/orders/{id}/status` | delivery partner |
| AI | `POST /ai/insights` body `{ "question": "..." }` | customer |
| Health | `GET /health` | public |

Status codes used: `200/201/204` success, `400` business-rule violation (invalid transition, unavailable dish...), `401` missing/invalid token, `403` wrong role, `404` not found **or not yours**, `409` duplicate (email, review, return), `422` validation error, `429` rate limited, `502/503/504` AI service problems.

### Payments and refunds (dummy)

No payment gateway is involved. Placing an order sets `payment_status = mock_paid` and writes a `mock_payment` row to `payment_ledger`. Approving a return sets the order to `REFUNDED`, `payment_status = refunded`, and writes a `refund` ledger row. Rejecting sets `return_status = rejected`.

### AI order insights

`POST /ai/insights` loads **only the authenticated customer's** orders (the customer id comes from the JWT, never from the request), builds a compact text context plus a few pre-computed facts (spend this week, undelivered orders, most-ordered items), and sends it with the question to OpenAI. The key stays in backend environment variables. Errors are mapped to clear responses (`429` with `Retry-After` for OpenAI rate limits and for the per-user limiter, `504` timeouts, `502` upstream errors, `503` when not configured).

### Middleware and background job

- **Middleware** logs every request (`method path`), adds `X-Process-Time-ms` and `X-Request-ID` response headers, and returns clean JSON on unexpected errors.
- **Reminder job** runs inside the API process every `REMINDER_INTERVAL_SECONDS`. Orders in `PLACED`/`ACCEPTED` whose status has not changed for more than `REMINDER_THRESHOLD_MINUTES` get one `admin_reminder_logs` row (no duplicates); it is auto-resolved when the order moves on. Owners see them on their dashboard. Because the job lives in the app process, run a **single** uvicorn worker (as the Dockerfile does).

## Tests

```bash
cd backend
pip install -r requirements.txt pytest
python -m pytest -q                                    # uses a temporary SQLite database
TEST_DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/test python -m pytest -q   # against PostgreSQL
```

The suite (19 tests) covers auth, RBAC, the full order lifecycle and invalid transitions, cancellation rules, dummy payment, reviews, returns/refunds, data isolation between customers, filters/pagination, reminders, menu CRUD, middleware headers and the AI feature (OpenAI is mocked, including its error paths).

## Security notes

- Passwords hashed with bcrypt; JWTs signed with `JWT_SECRET` and verified on every protected request.
- Every protected endpoint checks the role on the server; data access is scoped by the authenticated user (a customer cannot read another customer's order, an owner only sees their own restaurant, a delivery partner only sees their assignments).
- Order prices are always read from the database, never trusted from the client.
- The JWT is kept in `localStorage` as the assignment specifies; note that this makes it readable by any script running on the page, so avoid injecting untrusted HTML.
