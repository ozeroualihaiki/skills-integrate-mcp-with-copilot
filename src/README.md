# Mergington High School Activities API

A FastAPI application for viewing extracurricular activities and managing student registrations with authenticated school accounts.

## Getting started

1. Install the application dependencies:

   ```sh
   pip install -r requirements.txt
   ```

2. Set a session signing key. Use a new, private value of at least 32 characters:

   ```sh
   export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
   ```

   For production, also set `APP_ENV=production` and `SESSION_HTTPS_ONLY=true`. Production startup fails unless both the session secret and secure-cookie setting are configured.

3. Create accounts interactively. Passwords are prompted without echo and stored as scrypt hashes in the git-ignored `users.json` file:

   ```sh
   python -m src.manage_users admin@mergington.edu admin
   python -m src.manage_users organizer@mergington.edu organizer
   python -m src.manage_users student@mergington.edu student
   ```

   Assign admin accounts only to trusted administrators. To store account data elsewhere, set `USERS_FILE` to the desired path.

4. Start the application from the repository root:

   ```sh
   uvicorn src.app:app --reload
   ```

5. Open http://localhost:8000. API documentation is available at `/docs`.

When running locally without `SESSION_SECRET`, the app generates a temporary secret and logs a warning; sessions will be invalidated after restart. Configure a stable secret for persistent sessions.

## Authentication and permissions

- The activity list remains publicly viewable.
- Student accounts can register and unregister only themselves.
- Organizer and admin accounts can manage student registrations.
- Login uses a signed session cookie. Mutating requests require the session's CSRF token in the `X-CSRF-Token` header.
- Passwords use scrypt hashes; plaintext passwords are never written to the account file.
- Accounts must be provisioned by an operator with the `manage_users` command; there is no public account-creation endpoint.

## API endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/activities` | List activities and participants |
| POST | `/auth/login` | Sign in with a school email and password |
| GET | `/auth/me` | Get the current account and CSRF token |
| POST | `/auth/logout` | Sign out |
| POST | `/activities/{activity_name}/signup` | Register the signed-in student, or a student as an organizer/admin |
| DELETE | `/activities/{activity_name}/unregister` | Unregister the signed-in student, or a student as an organizer/admin |

For signup/unregister requests, organizers and admins specify the student using the `email` query parameter. A signed-in student does not provide an email; the app uses their authenticated account identity.

## Tests

Install test dependencies and run the focused API tests:

```sh
pip install -r requirements-dev.txt
python -m unittest discover -s tests
```

Activity and registration data is currently stored in memory and resets when the server restarts.
