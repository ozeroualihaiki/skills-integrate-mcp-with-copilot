"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import logging
import os
from pathlib import Path
import secrets

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from src.auth import hash_password, load_users, verify_password

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=current_dir / "static"), name="static")

logger = logging.getLogger(__name__)
users_file = Path(os.environ.get("USERS_FILE", current_dir.parent / "users.json"))
session_secret = os.environ.get("SESSION_SECRET")
if not session_secret:
    if os.environ.get("APP_ENV") == "production":
        raise RuntimeError("SESSION_SECRET must be configured in production")
    session_secret = secrets.token_urlsafe(32)
    logger.warning("SESSION_SECRET is unset; sessions will expire when the app restarts")
elif len(session_secret) < 32:
    raise RuntimeError("SESSION_SECRET must be at least 32 characters")

secure_cookies = os.environ.get("SESSION_HTTPS_ONLY", "").lower() == "true"
if os.environ.get("APP_ENV") == "production" and not secure_cookies:
    raise RuntimeError("SESSION_HTTPS_ONLY=true is required in production")

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    same_site="lax",
    https_only=secure_cookies,
)

dummy_password_hash = hash_password("not-a-real-user-password")


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


def current_user(request: Request) -> dict[str, str]:
    email = request.session.get("email")
    role = request.session.get("role")
    if not email or not role:
        raise HTTPException(status_code=401, detail="Authentication required")
    return {"email": email, "role": role}


def require_csrf(request: Request) -> None:
    token = request.session.get("csrf_token")
    supplied_token = request.headers.get("X-CSRF-Token")
    if not token or not supplied_token or not secrets.compare_digest(token, supplied_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")


def require_role(user: dict[str, str], *roles: str) -> None:
    if user["role"] not in roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")


def get_configured_users() -> dict[str, dict[str, str]]:
    try:
        return load_users(users_file)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured. Create a user account first.",
        ) from exc
    except (OSError, ValueError) as exc:
        logger.exception("Unable to load configured user accounts")
        raise HTTPException(
            status_code=500, detail="User account configuration is invalid"
        ) from exc

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


@app.post("/auth/login")
def login(credentials: LoginRequest, request: Request):
    users = get_configured_users()
    account = users.get(credentials.email.strip().lower())
    password_hash = account["password_hash"] if account else dummy_password_hash
    password_is_valid = verify_password(credentials.password, password_hash)
    if not account or not password_is_valid:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    request.session.clear()
    request.session.update(
        {
            "email": account["email"],
            "role": account["role"],
            "csrf_token": secrets.token_urlsafe(32),
        }
    )
    return {
        "email": account["email"],
        "role": account["role"],
        "csrf_token": request.session["csrf_token"],
    }


@app.get("/auth/me")
def get_current_user(request: Request):
    if not request.session.get("email"):
        return {"user": None, "csrf_token": None}
    return {
        "user": {
            "email": request.session["email"],
            "role": request.session["role"],
        },
        "csrf_token": request.session["csrf_token"],
    }


@app.post("/auth/logout")
def logout(request: Request):
    current_user(request)
    require_csrf(request)
    request.session.clear()
    return {"message": "Signed out"}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str, request: Request, email: str | None = None
):
    """Sign up the authenticated student or let an organizer manage a student."""
    user = current_user(request)
    require_csrf(request)
    if user["role"] == "student":
        if email and email.strip().lower() != user["email"]:
            raise HTTPException(
                status_code=403, detail="Students can only register themselves"
            )
        email = user["email"]
    else:
        require_role(user, "organizer", "admin")
        email = email.strip().lower() if email else user["email"]

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
def unregister_from_activity(
    activity_name: str, request: Request, email: str | None = None
):
    """Unregister the authenticated student or let an organizer manage a student."""
    user = current_user(request)
    require_csrf(request)
    if user["role"] == "student":
        if email and email.strip().lower() != user["email"]:
            raise HTTPException(
                status_code=403, detail="Students can only unregister themselves"
            )
        email = user["email"]
    else:
        require_role(user, "organizer", "admin")
        if not email:
            raise HTTPException(
                status_code=422,
                detail="Organizers must provide the student's email",
            )
        email = email.strip().lower()

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
