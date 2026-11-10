# Mergington High School Activities API

A super simple FastAPI application that lets visitors view extracurricular activities and teachers manage signups.

## Features

- View all available extracurricular activities
- Teacher login to sign up or unregister students

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Add teacher accounts to `teachers.json`. Store password hashes, not plaintext passwords. Generate a hash with:

   ```
   python -c "import hashlib, getpass, secrets; password=getpass.getpass(); salt=secrets.token_bytes(16); digest=hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600000).hex(); print(f'pbkdf2_sha256$600000${salt.hex()}${digest}')"
   ```

   Add each account as `{"username": "teacher-name", "password_hash": "..."}` in the `teachers` array.

3. Generate and configure a persistent secret for signed teacher sessions, then run the application:

   ```
   export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
   uvicorn app:app --app-dir src
   ```

   Set `COOKIE_SECURE=true` when serving over HTTPS. For local development, the server generates a temporary session secret if `SESSION_SECRET` is omitted; sessions then expire when the process restarts.

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | View activities and participant lists                               |
| GET    | `/auth/me`                                                        | Check whether the current visitor is logged in as a teacher          |
| POST   | `/auth/login`                                                     | Log in with a teacher username and password                          |
| POST   | `/auth/logout`                                                    | Log out                                                             |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up a student (teacher login required)                           |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher login required)                      |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity rosters are stored in memory and reset when the server restarts. Teacher password hashes are read from `teachers.json`.
