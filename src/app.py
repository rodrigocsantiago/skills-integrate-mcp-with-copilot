"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

SESSION_COOKIE = "teacher_session"
SESSION_MAX_AGE = 8 * 60 * 60
session_secret = os.environ.get("SESSION_SECRET")
SESSION_SECRET = session_secret.encode("utf-8") if session_secret else secrets.token_bytes(32)
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "").lower() in {"1", "true", "yes"}
TEACHERS_FILE = Path(os.environ.get("TEACHERS_FILE", current_dir / "teachers.json"))


def load_teachers():
    try:
        with TEACHERS_FILE.open(encoding="utf-8") as credentials_file:
            data = json.load(credentials_file)
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Unable to load teacher credentials from {TEACHERS_FILE}") from error

    if not isinstance(data, dict) or not isinstance(data.get("teachers"), list):
        raise RuntimeError("Teacher credentials must contain a 'teachers' list")

    teachers = {}
    for teacher in data["teachers"]:
        if (
            not isinstance(teacher, dict)
            or not isinstance(teacher.get("username"), str)
            or not teacher["username"]
            or not isinstance(teacher.get("password_hash"), str)
        ):
            raise RuntimeError("Each teacher must have a username and password_hash")
        if parse_password_hash(teacher["password_hash"]) is None:
            raise RuntimeError(f"Invalid password hash for teacher {teacher['username']}")
        if teacher["username"] in teachers:
            raise RuntimeError(f"Duplicate teacher username: {teacher['username']}")
        teachers[teacher["username"]] = teacher["password_hash"]
    return teachers


def parse_password_hash(password_hash: str):
    try:
        algorithm, iterations, salt_hex, expected_hash = password_hash.split("$")
        iteration_count = int(iterations)
        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(expected_hash)
    except (ValueError, TypeError):
        return None

    if (
        algorithm != "pbkdf2_sha256"
        or not 100_000 <= iteration_count <= 2_000_000
        or not salt
        or len(expected_digest) != hashlib.sha256().digest_size
    ):
        return None
    return iteration_count, salt, expected_digest


teachers = load_teachers()


def verify_password(password: str, password_hash: str) -> bool:
    parsed_hash = parse_password_hash(password_hash)
    if parsed_hash is None:
        return False

    iteration_count, salt, expected_digest = parsed_hash
    actual_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iteration_count
    )
    return hmac.compare_digest(actual_digest, expected_digest)


def create_session_token(username: str) -> str:
    payload = json.dumps(
        {"username": username, "expires": int(time.time()) + SESSION_MAX_AGE},
        separators=(",", ":"),
    ).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(
        SESSION_SECRET, encoded_payload.encode("ascii"), hashlib.sha256
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{encoded_payload}.{encoded_signature}"


def get_teacher_from_session(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None

    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        signature = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )
        expected_signature = hmac.new(
            SESSION_SECRET, encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(signature, expected_signature):
            return None

        payload_bytes = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )
        payload = json.loads(payload_bytes)
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error):
        return None

    if not isinstance(payload, dict):
        return None

    username = payload.get("username")
    expires = payload.get("expires")
    if (
        not isinstance(username, str)
        or not isinstance(expires, int)
        or isinstance(expires, bool)
        or expires < time.time()
        or username not in teachers
    ):
        return None
    return username


def require_teacher(request: Request):
    username = get_teacher_from_session(request)
    if username is None:
        raise HTTPException(status_code=401, detail="Teacher login required")
    return username


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)


@app.get("/auth/me")
def get_session(request: Request):
    username = get_teacher_from_session(request)
    return {"authenticated": username is not None, "username": username}


@app.post("/auth/login")
def login(credentials: LoginRequest, response: Response):
    password_hash = teachers.get(credentials.username)
    if password_hash is None or not verify_password(credentials.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(credentials.username),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return {"message": "Logged in"}


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        SESSION_COOKIE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return {"message": "Logged out"}


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, _: str = Depends(require_teacher)):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, _: str = Depends(require_teacher)):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
