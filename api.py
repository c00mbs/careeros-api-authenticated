
"""CareerOS API backend."""

from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from modules.career_dna import build_career_dna
from modules.models import (
    APPLICATION_STATUSES,
    Application,
    CareerEvent,
    Certification,
    Resume,
    Skill,
    User,
)
from modules.orm_database import SessionLocal, initialize_orm_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_orm_database()
    yield


app = FastAPI(
    title="CareerOS API",
    description="Career profiles, skills, resumes, and job tracking.",
    version="0.1.0",
    lifespan=lifespan,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Request and response schemas ----------

class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=3, max_length=320)


class UserOut(UserCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ResumeCreate(BaseModel):
    user_id: int
    title: str = Field(min_length=1, max_length=200)
    version: str = Field(default="1.0", min_length=1, max_length=50)
    content: str = Field(min_length=1)


class ResumeOut(ResumeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ApplicationCreate(BaseModel):
    user_id: int
    company: str = Field(min_length=1, max_length=200)
    job_title: str = Field(min_length=1, max_length=200)
    status: str = "Saved"
    applied_date: Optional[date] = None


class ApplicationOut(ApplicationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class SkillCreate(BaseModel):
    user_id: int
    skill_name: str = Field(min_length=1, max_length=100)
    proficiency: int = Field(default=3, ge=1, le=5)


class SkillOut(SkillCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class CertificationCreate(BaseModel):
    user_id: int
    name: str = Field(min_length=1, max_length=200)
    provider: str = Field(min_length=1, max_length=200)
    completion_date: Optional[date] = None


class CertificationOut(CertificationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class CareerEventCreate(BaseModel):
    user_id: int
    type: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    date: date


class CareerEventOut(CareerEventCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Helpers ----------

def require_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def commit_or_rollback(db: Session):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The record conflicts with existing data or violates a constraint.",
        ) from exc


# ---------- Service and health ----------

@app.get("/")
def root():
    return {
        "service": "CareerOS API",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="Database unavailable"
        ) from exc


# ---------- Users ----------

@app.post("/users", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    user = User(
        name=payload.name.strip(),
        email=payload.email.strip().lower(),
    )
    db.add(user)
    commit_or_rollback(db)
    db.refresh(user)
    return user


@app.get("/users", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
):
    return db.scalars(
        select(User).order_by(User.id.desc()).limit(limit)
    ).all()


# ---------- Resumes ----------

@app.post("/resumes", response_model=ResumeOut, status_code=201)
def create_resume(payload: ResumeCreate, db: Session = Depends(get_db)):
    require_user(db, payload.user_id)
    resume = Resume(**payload.model_dump())
    db.add(resume)
    commit_or_rollback(db)
    db.refresh(resume)
    return resume


@app.get("/resumes", response_model=list[ResumeOut])
def list_resumes(user_id: int, db: Session = Depends(get_db)):
    require_user(db, user_id)
    return db.scalars(
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.id.desc())
    ).all()


# ---------- Job applications ----------

@app.post(
    "/applications",
    response_model=ApplicationOut,
    status_code=201,
)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
):
    require_user(db, payload.user_id)

    if payload.status not in APPLICATION_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Status must be one of: {', '.join(APPLICATION_STATUSES)}",
        )

    application = Application(**payload.model_dump())
    db.add(application)
    commit_or_rollback(db)
    db.refresh(application)
    return application


@app.get("/applications", response_model=list[ApplicationOut])
def list_applications(
    user_id: int,
    db: Session = Depends(get_db),
    status: Optional[str] = None,
):
    require_user(db, user_id)

    statement = select(Application).where(
        Application.user_id == user_id
    )

    if status is not None:
        if status not in APPLICATION_STATUSES:
            raise HTTPException(
                status_code=422,
                detail=f"Status must be one of: {', '.join(APPLICATION_STATUSES)}",
            )
        statement = statement.where(Application.status == status)

    return db.scalars(
        statement.order_by(Application.id.desc())
    ).all()


# ---------- Skills ----------

@app.post("/skills", response_model=SkillOut, status_code=201)
def create_skill(payload: SkillCreate, db: Session = Depends(get_db)):
    require_user(db, payload.user_id)
    skill = Skill(**payload.model_dump())
    db.add(skill)
    commit_or_rollback(db)
    db.refresh(skill)
    return skill


@app.get("/skills", response_model=list[SkillOut])
def list_skills(user_id: int, db: Session = Depends(get_db)):
    require_user(db, user_id)
    return db.scalars(
        select(Skill)
        .where(Skill.user_id == user_id)
        .order_by(Skill.skill_name)
    ).all()


# ---------- Certifications ----------

@app.post(
    "/certifications",
    response_model=CertificationOut,
    status_code=201,
)
def create_certification(
    payload: CertificationCreate,
    db: Session = Depends(get_db),
):
    require_user(db, payload.user_id)
    certification = Certification(**payload.model_dump())
    db.add(certification)
    commit_or_rollback(db)
    db.refresh(certification)
    return certification


@app.get(
    "/certifications",
    response_model=list[CertificationOut],
)
def list_certifications(user_id: int, db: Session = Depends(get_db)):
    require_user(db, user_id)
    return db.scalars(
        select(Certification)
        .where(Certification.user_id == user_id)
        .order_by(Certification.id.desc())
    ).all()


# ---------- Career timeline ----------

@app.post(
    "/career-events",
    response_model=CareerEventOut,
    status_code=201,
)
def create_career_event(
    payload: CareerEventCreate,
    db: Session = Depends(get_db),
):
    require_user(db, payload.user_id)
    event = CareerEvent(**payload.model_dump())
    db.add(event)
    commit_or_rollback(db)
    db.refresh(event)
    return event


@app.get(
    "/career-timeline",
    response_model=list[CareerEventOut],
)
def career_timeline(user_id: int, db: Session = Depends(get_db)):
    require_user(db, user_id)
    return db.scalars(
        select(CareerEvent)
        .where(CareerEvent.user_id == user_id)
        .order_by(CareerEvent.date.desc(), CareerEvent.id.desc())
    ).all()


# ---------- Career intelligence ----------

@app.get("/career-dna")
def career_dna(user_id: int, db: Session = Depends(get_db)):
    user = require_user(db, user_id)
    return {
        "user_id": user.id,
        "name": user.name,
        "career_dna": build_career_dna(user),
    }


@app.get("/career-summary")
def career_summary(user_id: int, db: Session = Depends(get_db)):
    user = require_user(db, user_id)

    applications = db.scalars(
        select(Application).where(Application.user_id == user_id)
    ).all()
    skills = db.scalars(
        select(Skill).where(Skill.user_id == user_id)
    ).all()
    certifications = db.scalars(
        select(Certification).where(Certification.user_id == user_id)
    ).all()
    events = db.scalars(
        select(CareerEvent).where(CareerEvent.user_id == user_id)
    ).all()

    status_counts = {
        status: sum(
            1 for application in applications
            if application.status == status
        )
        for status in APPLICATION_STATUSES
    }

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
        "counts": {
            "applications": len(applications),
            "skills": len(skills),
            "certifications": len(certifications),
            "career_events": len(events),
        },
        "applications_by_status": status_counts,
        "career_dna": build_career_dna(user),
                              }

