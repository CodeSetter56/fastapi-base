# FastAPI Base

A small, reusable FastAPI starter with JWT authentication, PostgreSQL,
SQLModel, and Alembic migrations.

## What is included

- **Users** with hashed passwords (bcrypt).
- **Roles** (`user` / `admin`). The first registered account becomes the admin;
  admins can manage every account.
- **Items** owned by users (a ready example of a user-owned resource).
- **Access + refresh tokens** (PyJWT), usable as a Bearer header or HttpOnly
  cookies. Logging out bumps a per-user token version, invalidating all tokens.
- **CSRF protection** for cookie-authenticated requests.
- **Pagination** on all list endpoints.
- **CORS** with configurable origins.
- **A consistent error envelope** for HTTP and validation errors.
- **Pydantic v2** request/response schemas with validation.
- **SQLModel** table models over an async SQLAlchemy session.
- **Alembic** migrations with autogenerate from the SQLModel metadata.
- **Docker Compose** with PostgreSQL, Adminer, and the API.

## Project layout

```text
src/fastapi_base/
├── main.py              # FastAPI app, lifespan, middleware, routers
├── config.py            # Settings from environment / .env
├── db.py                # async engine, session factory, session dependency
├── models.py            # SQLModel table models (User, Item) and UserRole
├── security.py          # Password hashing and JWT creation/decoding
├── cookies.py           # Auth cookie helpers
├── csrf.py              # Double-submit CSRF middleware
├── errors.py            # Error envelope and exception handlers
├── deps.py              # get_current_user / get_current_admin dependencies
├── schemas/             # Pydantic request/response models (Page is here)
├── services/            # Business rules, queries, and error handling
└── routers/             # HTTP endpoints
alembic/                 # Migration environment and versions
```

Data flows in one direction: `router -> service -> SQLModel -> PostgreSQL`.
Routers deal with HTTP, services with rules/queries, and models with storage.

## Quick start with Docker

```bash
docker compose up --build
```

| Service | URL |
| --- | --- |
| API docs (Swagger) | http://localhost:8000/docs |
| API health | http://localhost:8000/health |
| Adminer | http://localhost:8080 |

Adminer login: system **PostgreSQL**, server **db**, username **postgres**,
password **postgres**, database **fastapi_base**.

Migrations run automatically when the API container starts.

## Local development

```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env

docker compose up -d db
uv sync
uv run alembic upgrade head
uv run uvicorn fastapi_base.main:app --reload
```

Then open http://localhost:8000/docs.

Change `JWT_SECRET` in `.env` before deploying. Production secrets should come
from your platform's secret manager, not a committed file.

## Endpoints

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/auth/register` | No | Create a user |
| `POST` | `/auth/login` | No | Get an access + refresh token pair |
| `POST` | `/auth/refresh` | Refresh token | Get a new token pair |
| `POST` | `/auth/logout` | Access token | Invalidate all of the user's tokens |
| `GET` | `/users` | Admin | Paginated user list |
| `GET` | `/users/me` | Access token | Current user |
| `GET` | `/users/{id}` | Self or admin | Get a user |
| `PATCH` | `/users/{id}` | Self or admin | Update email/password |
| `PATCH` | `/users/{id}/role` | Admin | Change a user's role |
| `DELETE` | `/users/{id}` | Self or admin | Delete an account and its items |
| `GET` | `/items` | Access token | Paginated list of the current user's items |
| `POST` | `/items` | Access token | Create an item |
| `GET` | `/items/{id}` | Access token | Get one of the current user's items |
| `PATCH` | `/items/{id}` | Access token | Update an item |
| `DELETE` | `/items/{id}` | Access token | Delete an item |

Authenticated requests can use either transport:

- `Authorization: Bearer <access_token>` — best for API clients and Swagger.
- The `access_token` cookie set by `/auth/login` — best for browsers. Cookie
  requests to `POST`/`PATCH`/`DELETE` must also send `X-CSRF-Token` with the
  value of the readable `csrf_token` cookie. Bearer requests do not need it.

The last remaining admin cannot be demoted or deleted (`409`), so you cannot
lock yourself out. Changing a password bumps the user's token version, so every
previously issued token stops working and the client must log in again.

### Roles

Roles are `user` and `admin`. Bootstrap works in two ways:

- On a fresh database, the first account to register becomes the admin.
- The `0002` migration promotes the oldest existing account when upgrading a
  database created before roles existed.
- After that, an admin changes roles with `PATCH /users/{id}/role`.

Admins can list, read, update, and delete any account. Regular users can only
read and modify themselves.

### Cookie authentication

`POST /auth/login` sets three cookies:

| Cookie | HttpOnly | Purpose |
| --- | --- | --- |
| `access_token` | Yes | Authenticates requests |
| `refresh_token` | Yes | Used by `/auth/refresh`, scoped to `/auth` |
| `csrf_token` | No | Copied into the `X-CSRF-Token` header by JavaScript |

`POST /auth/refresh` accepts the refresh token from the cookie or the JSON body.
`POST /auth/logout` clears all three cookies and invalidates the user's tokens.
Set `COOKIE_SECURE=true` when serving over HTTPS.

### Pagination

List endpoints accept `limit` (1–100, default 20) and `offset` (default 0):

```bash
GET /items?limit=20&offset=0
```

```json
{
  "items": [],
  "total": 0,
  "limit": 20,
  "offset": 0
}
```

### Errors

All errors use the same envelope:

```json
{
  "error": {
    "code": "not_found",
    "message": "User not found"
  }
}
```

Validation errors additionally include `error.details`, a list of
`{"field", "message", "type"}` objects. Codes include `bad_request`,
`unauthorized`, `forbidden`, `not_found`, `conflict`, `validation_error`, and
`internal_error`.

### Authorizing in Swagger

Swagger does not apply the login response automatically. After calling
`/auth/login`, copy the **`access_token`** value (not `refresh_token`), click the
**Authorize** button at the top of the docs page, paste the raw token without a
`Bearer ` prefix, click **Authorize** in the dialog, then close it. The lock
icons should now show as locked.

The browser also receives the auth cookies from `/auth/login`, but Swagger UI
does not send the `X-CSRF-Token` header, so cookie-authenticated `POST`,
`PATCH`, and `DELETE` requests are rejected. Use the **Authorize** button
(Bearer) while working in Swagger; the CSRF check only applies to cookie auth.

### Example flow

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"secret123"}'

curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"secret123"}'
```

The login response contains `access_token` and `refresh_token` and also sets
them as cookies. Access tokens expire after 15 minutes by default; use the
refresh token at `/auth/refresh` to get a new pair. Refresh tokens are stateless
and remain valid until they expire or the user logs out (which invalidates all
of that user's tokens). Login, refresh, and register accept and return JSON
(not OAuth2 form data).

## Migrations

After changing or adding a SQLModel in `models.py`, generate a migration:

```bash
uv run alembic revision --autogenerate -m "add notes table"
```

Review the generated file in `alembic/versions/` before applying it. Alembic
compares the SQLModel metadata in `models.py` with the live database.

```bash
uv run alembic upgrade head
```

With Docker Compose, the `alembic/` directory is mounted into the container, so
this also works:

```bash
docker compose exec api alembic revision --autogenerate -m "add notes table"
docker compose exec api alembic upgrade head
```

The initial migration was written by hand because it created the baseline
schema; subsequent schema changes can be autogenerated.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/fastapi_base` | Database connection string |
| `JWT_SECRET` | dev value | JWT signing secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `CORS_ORIGINS` | empty | Comma-separated allowed browser origins |
| `COOKIE_SECURE` | `false` | Set `true` when serving over HTTPS |
| `COOKIE_SAMESITE` | `lax` | Cookie SameSite policy (`lax`, `strict`, `none`) |
| `POSTGRES_USER` | `postgres` | Docker Compose database user |
| `POSTGRES_PASSWORD` | `postgres` | Docker Compose database password |
| `POSTGRES_DB` | `fastapi_base` | Docker Compose database name |
| `POSTGRES_PORT` | `5432` | Host port for PostgreSQL |

## Adding another user-owned resource

1. Add a SQLModel class in `models.py` with a foreign key to `users.id` and
   `ondelete="CASCADE"`.
2. Run `uv run alembic revision --autogenerate -m "add notes table"` and review
   the generated migration.
3. Add `schemas/<resource>.py`.
4. Add `services/<resource>.py` for queries, ownership, and not-found rules.
5. Add `routers/<resource>.py` and register it in `main.py`.
