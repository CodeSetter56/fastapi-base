# FastAPI Base Backend

A robust, production-grade FastAPI asynchronous backend featuring SQLModel, PostgreSQL, Alembic migrations, JWT authentication with token version revocation, Google OAuth2 login, role-based access control (RBAC) with last admin protection, bookmarks, ratings & reviews, shopping cart, and categories & tags.

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
