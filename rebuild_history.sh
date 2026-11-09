#!/usr/bin/env bash
# Rebuilds git history as small commits, in dependency order.
# Run from the root of your project folder (the one with pyproject.toml), on a COPY or after backing up.
set -euo pipefail
[ -f pyproject.toml ] || { echo "run this from the project root"; exit 1; }
rm -rf .git
git init -q -b main

c() {  # c "message" path...
  local msg="$1"; shift
  git add -- "$@"
  git commit -q -m "$msg"
  echo "committed: $msg"
}

P=src/fastapi_base
c "chore: project setup (deps, python version, ignore files, readme)" \
  .gitignore .dockerignore .python-version pyproject.toml uv.lock README.md
c "feat(config): load settings from environment" $P/__init__.py $P/config.py
c "feat(db): async engine and session dependency" $P/db.py
c "feat(middleware): consistent error envelope and handlers" $P/middleware/__init__.py $P/middleware/errors.py
c "feat(models): user and item tables" $P/models.py
c "build(alembic): migration environment" alembic.ini alembic/env.py alembic/script.py.mako
c "feat(db): initial migrations" alembic/versions
c "feat(security): password hashing and JWT helpers" $P/token/security.py
c "feat(schemas): shared pagination schema" $P/schemas/__init__.py $P/schemas/common.py
c "feat(schemas): user schemas" $P/schemas/user.py
c "feat(schemas): auth token schemas" $P/schemas/auth.py
c "feat(schemas): item schemas" $P/schemas/item.py
c "feat(auth): auth cookie helpers" $P/token/cookies.py
c "feat(middleware): CSRF protection" $P/middleware/csrf.py
c "feat(auth): current-user dependency" $P/deps.py
c "feat(auth): register, login, refresh and logout service" $P/services/__init__.py $P/services/auth.py
c "feat(users): user service with roles and last-admin protection" $P/services/users.py
c "feat(items): item service" $P/services/items.py
c "feat(auth): Google OAuth service" $P/services/oauth.py
c "feat(api): auth routes" $P/routers/__init__.py $P/routers/auth.py
c "feat(api): user routes" $P/routers/users.py
c "feat(api): item routes" $P/routers/items.py
c "feat(app): wire up FastAPI app, CORS and middleware" $P/main.py
c "build(docker): Dockerfile and docker-compose" Dockerfile docker-compose.yml

left=$(git ls-files --others --exclude-standard)
[ -z "$left" ] && echo "all files committed" || { echo "NOT COMMITTED:"; echo "$left"; }