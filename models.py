"""SQLAlchemy models for accounts and career profiles."""

from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


APPLICATION_STATUSES = (
    "Saved",
    "Interested",
    "Applied",
    "Interviewing",
    "Offer",
    "Closed",
)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_users_name_not_blank"),
        CheckConstraint("length(trim(email)) > 0", name="ck_users_email_not_blank"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)

    auth_credential: Mapped["AuthCredential | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    resumes: Mapped[list["Resume"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    skills: Mapped[list["Skill"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    certifications: Mapped[list["Certification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    career_events: Mapped[list["CareerEvent"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AuthCredential(Base):
    """One-way password hash, stored separately from public user profile data."""

    __tablename__ = "auth_credentials"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    user: Mapped[User] = relationship(back_populates="auth_credential")


class Resume(Base):
    __tablename__ = "resumes"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="ck_resumes_title_not_blank"),
        CheckConstraint("length(trim(version)) > 0", name="ck_resumes_version_not_blank"),
        CheckConstraint("length(trim(content)) > 0", name="ck_resumes_content_not_blank"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user: Mapped[User] = relationship(back_populates="resumes")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint("length(trim(company)) > 0", name="ck_applications_company_not_blank"),
        CheckConstraint("length(trim(job_title)) > 0", name="ck_applications_job_title_not_blank"),
        CheckConstraint(
            "status IN ('Saved', 'Interested', 'Applied', 'Interviewing', 'Offer', 'Closed')",
            name="ck_applications_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    job_title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Saved")
    applied_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    user: Mapped[User] = relationship(back_populates="applications")
    interviews: Mapped[list["Interview"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (
        CheckConstraint("length(trim(skill_name)) > 0", name="ck_skills_name_not_blank"),
        CheckConstraint("proficiency BETWEEN 1 AND 5", name="ck_skills_proficiency_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_name: Mapped[str] = mapped_column(String(100), nullable=False)
    proficiency: Mapped[int] = mapped_column(Integer, nullable=False)
    user: Mapped[User] = relationship(back_populates="skills")


class Certification(Base):
    __tablename__ = "certifications"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_certifications_name_not_blank"),
        CheckConstraint("length(trim(provider)) > 0", name="ck_certifications_provider_not_blank"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider: Mapped[str] = mapped_column(String(200), nullable=False)
    completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    user: Mapped[User] = relationship(back_populates="certifications")


class Interview(Base):
    __tablename__ = "interviews"
    __table_args__ = (
        CheckConstraint(
            "length(trim(round_name)) > 0", name="ck_interviews_round_name_not_blank"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    round_name: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(String(50), nullable=True)
    application: Mapped[Application] = relationship(back_populates="interviews")


class CareerEvent(Base):
    __tablename__ = "career_events"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="ck_career_events_title_not_blank"),
        CheckConstraint("length(trim(type)) > 0", name="ck_career_events_type_not_blank"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    user: Mapped[User] = relationship(back_populates="career_events")
