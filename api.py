"""Authenticated FastAPI entry point for CareerOS."""

from contextlib import asynccontextmanager
from datetime import date

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

load_dotenv()

from modules.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    validate_auth_settings,
    verify_password,
)
from modules.career_dna import build_career_dna
from modules.models import (
    Application,
    AuthCredential,
    CareerEvent,
    Certification,
    Interview,
    Skill,
    User,
)
from modules.orm_database import SessionLocal, initialize_orm_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_auth_settings()
    initialize_orm_database()
    yield


def get_db():
    with SessionLocal() as session:
        yield session


app = FastAPI(title="CareerOS API", lifespan=lifespan)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=128)


class UserResponse(BaseModel):
    id: int
    name: str
    email: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    local, separator, domain = normalized.partition("@")
    if not separator or not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise HTTPException(status_code=422, detail="A valid email address is required")
    return normalized


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_access_token(token)
    except (jwt.PyJWTError, RuntimeError):
        raise unauthorized from None
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "CareerOS API Running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    email = normalize_email(payload.email)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be blank")
    if db.scalar(select(User.id).where(func.lower(User.email) == email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    user = User(name=name, email=email)
    user.auth_credential = AuthCredential(password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered") from None
    db.refresh(user)
    return user


@app.post("/auth/token", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> TokenResponse:
    try:
        email = normalize_email(form.username)
    except HTTPException:
        email = ""
    user = db.scalar(select(User).where(func.lower(User.email) == email)) if email else None
    credential = user.auth_credential if user is not None else None
    if credential is None or not verify_password(form.password, credential.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, lifetime = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=lifetime)


@app.get("/auth/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@app.get("/applications")
def get_applications(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict[str, int | str | date | None]]:
    applications = db.scalars(
        select(Application)
        .where(Application.user_id == current_user.id)
        .order_by(Application.id.desc())
    ).all()
    return [
        {
            "id": item.id,
            "company": item.company,
            "title": item.job_title,
            "status": item.status,
            "applied_date": item.applied_date,
        }
        for item in applications
    ]


@app.get("/career-timeline")
def get_career_timeline(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[dict[str, str | int | None]]:
    events = db.scalars(
        select(CareerEvent)
        .where(CareerEvent.user_id == current_user.id)
        .order_by(CareerEvent.date.desc(), CareerEvent.id.desc())
    ).all()
    return [
        {"date": event.date.isoformat(), "type": event.type, "title": event.title}
        for event in events
    ]


@app.get("/career-dna")
def get_career_dna(current_user: User = Depends(get_current_user)) -> dict[str, int]:
    return build_career_dna(current_user)


@app.get("/career-summary")
def get_career_summary(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict[str, int | dict[str, int]]:
    user_id = current_user.id
    applications_count = db.scalar(
        select(func.count()).select_from(Application).where(Application.user_id == user_id)
    ) or 0
    interviews_count = db.scalar(
        select(func.count())
        .select_from(Interview)
        .join(Application, Interview.application_id == Application.id)
        .where(Application.user_id == user_id)
    ) or 0
    certifications_count = db.scalar(
        select(func.count()).select_from(Certification).where(Certification.user_id == user_id)
    ) or 0
    skills_count = db.scalar(
        select(func.count()).select_from(Skill).where(Skill.user_id == user_id)
    ) or 0
    career_events_count = db.scalar(
        select(func.count()).select_from(CareerEvent).where(CareerEvent.user_id == user_id)
    ) or 0

    return {
        "skills": skills_count,
        "certifications": certifications_count,
        "applications": applications_count,
        "interviews": interviews_count,
        "career_events": career_events_count,
        "dna": build_career_dna(current_user),
    }
