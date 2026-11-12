# FastAPI Base Backend

A robust, production-grade FastAPI asynchronous backend featuring SQLModel, PostgreSQL, Alembic migrations, JWT authentication with token version revocation, Google OAuth2 login, role-based access control (RBAC) with last admin protection, bookmarks, ratings & reviews, shopping cart, categories & tags, and S3 object storage (MinIO / Cloudflare R2).

## Features

- **Authentication & Authorization**:
  - JWT access and refresh tokens stored in secure HttpOnly cookies.
  - Double-submit CSRF protection middleware.
  - Google OAuth2 Authorization Code Flow with secure state validation and email verification.
  - RBAC (Admin / User) with last active admin safety protection (preventing deletion or demotion of the last remaining active admin).

- **Core Resources**:
  - **Items & Categories**: CRUD operations for items and categories with pagination and filtering.
  - **Bookmarks / Saved Items**: Users can bookmark/save items.
  - **Ratings & Reviews**: Users can rate and review items (1-5 stars, one rating per user per item with average score calculation).
  - **Shopping Cart**: Add, update quantity, remove, and clear cart items with quantity aggregation and total summary.
  - **Storage Service**: S3-compatible object storage (MinIO locally, Cloudflare R2 in production) via `aioboto3` with automatic image thumbnail generation and presigned URLs.

## Setup & Running

1. **Configure Environment**:
   Copy `.env.example` to `.env` and fill in database credentials and Google OAuth keys.

2. **Run Migrations**:
   ```bash
   alembic upgrade head
   ```

3. **Start the Development Server**:
   ```bash
   uvicorn fastapi_base.main:app --reload
   ```

---

## Database Schema & Entity Relationship Diagram

### Entity Relationship Diagram (ERD)

```text
┌────────────────────────────────────────────────────────┐
│                        users                           │
├────────────────────────────────────────────────────────┤
│ PK id (UUID)                                           │
│    email (Text, Unique)                                │
│    username (Text, Unique)                             │
│    password_hash (Text)                                │
│    role (Text: 'user' | 'admin')                       │
│    is_active (Boolean)                                 │
│    token_version (Integer)                             │
└───────────┬──────────────┬──────────────┬──────────────┘
            │ 1            │ 1            │ 1
            │              │              │
      N     │        N     │        N     │        N
┌───────────▼──┐   ┌───────▼──────┐   ┌───▼──────────┐   ┌──────────────────────┐
│    items     │   │  bookmarks   │   │   ratings    │   │      cart_items      │
├──────────────┤   ├──────────────┤   ├──────────────┤   ├──────────────────────┤
│ PK id        │   │ PK id        │   │ PK id        │   │ PK id                │
│ FK owner_id  │   │ FK user_id   │   │ FK user_id   │   │ FK user_id           │
│ FK cat_id    │   │ FK item_id   │   │ FK item_id   │   │ FK item_id           │
└───────┬──────┘   └──────────────┘   └──────────────┘   │ quantity (Int)       │
        │                                                └──────────────────────┘
        │ N
┌───────▼──────┐
│  categories  │
├──────────────┤
│ PK id        │
│    name      │
│    slug      │
└──────────────┘

┌────────────────────────────────────────────────────────┐
│                    file_attachments                    │
├────────────────────────────────────────────────────────┤
│ PK id (UUID)                                           │
│    owner_type (Text: 'user' | 'item')                  │
│    owner_id (UUID)                                     │
│    label (Text: 'avatar' | 'gallery' etc.)             │
│    file_key (Text)                                     │
│    thumb_key (Text)                                    │
│    filename (Text)                                     │
│    content_type (Text)                                 │
│    size_bytes (Integer)                                │
│    uploaded_by (UUID)                                  │
└────────────────────────────────────────────────────────┘
```

