# CareerOS API

FastAPI service for career profiles, application tracking, career timelines,
and Career DNA summaries. User accounts use Argon2 password hashes and signed,
short-lived JWT bearer tokens.

## Authentication design

- `POST /auth/register` creates a user and stores only an Argon2 password hash
  in the `auth_credentials` table. The password is never returned.
- `POST /auth/token` accepts OAuth2 form fields (`username` is the email) and
  returns a 30-minute JWT access token by default.
- Protected routes require `Authorization: Bearer <access_token>`. The API gets
  the user ID from the verified token subject; it does not accept a caller
  supplied `user_id` to choose whose private data is returned.
- `GET /auth/me` returns the authenticated user's public profile.
- `/` and `/health` are public. Career and application endpoints require a
  valid token and scope database queries to that token's user.

The JWT signing secret is provided through `JWT_SECRET_KEY` and must be at least
32 characters. Passwords must be 12–128 characters. Tokens expire; this MVP has
no refresh-token, logout/revocation, email-verification, or password-reset flow.
Deploy behind HTTPS. The OpenAPI docs at `/docs` include the OAuth2 bearer
security scheme.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `JWT_SECRET_KEY` in `.env` to a unique random secret. Generate one with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then start the service:

```powershell
python -m uvicorn api:app --reload
```

The API listens at `http://127.0.0.1:8000`; interactive docs are at
`http://127.0.0.1:8000/docs`. `DATABASE_URL` defaults to `sqlite:///careeros.db`.
At startup, SQLAlchemy creates missing tables, including `auth_credentials`,
without deleting existing profile tables.

## Example request flow

Register an account:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/auth/register `
  -ContentType 'application/json' `
  -Body '{"name":"Alex Example","email":"alex@example.com","password":"a-long-unique-password"}'
```

Exchange credentials for a token (OAuth2 form encoding):

```powershell
$token = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/auth/token `
  -ContentType 'application/x-www-form-urlencoded' `
  -Body 'username=alex%40example.com&password=a-long-unique-password'
```

Call a protected endpoint:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/career-summary `
  -Headers @{ Authorization = "Bearer $($token.access_token)" }
```

## Endpoints

| Endpoint | Access | Purpose |
| --- | --- | --- |
| `GET /` | Public | Service welcome |
| `GET /health` | Public | Deployment health check |
| `POST /auth/register` | Public | Create account |
| `POST /auth/token` | Public | Verify credentials and issue access token |
| `GET /auth/me` | Bearer token | Current user's profile |
| `GET /applications` | Bearer token | Current user's applications |
| `GET /career-timeline` | Bearer token | Current user's events, newest first |
| `GET /career-dna` | Bearer token | Current user's saved-skill scores |
| `GET /career-summary` | Bearer token | Current user's counts and Career DNA |

## Existing databases

The auth table is additive, so startup preserves existing user/profile data.
Existing users have no password hash and cannot sign in until an account-claim
or password-reset flow is deliberately added. Do not allow a registration to
claim an existing email without verifying ownership.

## Deploy to Render

Create a Render Blueprint from this repository using `render.yaml`. Set the
`JWT_SECRET_KEY` secret in the Render service environment before the service
starts. Render will provide an HTTPS `onrender.com` address after deployment.
