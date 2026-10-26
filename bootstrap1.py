from pathlib import Path

FILES = {}

FILES["requirements.txt"] = r'''fastapi>=0.115
uvicorn[standard]>=0.30
sqlalchemy>=2.0
pydantic>=2.7
pydantic-settings>=2.3
python-multipart>=0.0.9
PyJWT>=2.8
bcrypt>=4.1
email-validator>=2.1
'''

FILES[".env.example"] = r'''SMS_DATABASE_URL=sqlite:///./school.db
SMS_SECRET_KEY=change-me-to-a-long-random-string
SMS_CORS_ORIGINS=["http://localhost:3000"]
'''

FILES["app/__init__.py"] = ""
FILES["app/routers/__init__.py"] = ""

FILES["app/config.py"] = r'''from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SMS_")
    database_url: str = "sqlite:///./school.db"
    secret_key: str = "dev-insecure-change-me"
    algorithm: str = "HS256"
    access_token_minutes: int = 480
    cors_origins: list[str] = ["http://localhost:3000"]

@lru_cache
def get_settings() -> Settings:
    return Settings()
'''

FILES["app/database.py"] = r'''from collections.abc import Iterator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from app.config import get_settings
from app.models import Base

settings = get_settings()
_is_sqlite = settings.database_url.startswith("sqlite")
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if _is_sqlite else {}, pool_pre_ping=True)

@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _):
    if _is_sqlite:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db() -> None:
    Base.metadata.create_all(bind=engine)
'''

FILES["app/models.py"] = r'''from __future__ import annotations
import enum
from datetime import date, datetime, time
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, Time, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase): pass

class Role(str, enum.Enum):
    admin = "admin"
    teacher = "teacher"
    student = "student"
    guardian = "guardian"

class AttendanceStatus(str, enum.Enum):
    present = "present"
    absent = "absent"
    late = "late"
    excused = "excused"

class AssessmentType(str, enum.Enum):
    assignment = "assignment"
    quiz = "quiz"
    exam = "exam"
    project = "project"

class InvoiceStatus(str, enum.Enum):
    unpaid = "unpaid"
    partial = "partial"
    paid = "paid"
    void = "void"

class Audience(str, enum.Enum):
    all = "all"
    teachers = "teachers"
    students = "students"
    guardians = "guardians"
    section = "section"

def _enum(e, length: int = 20):
    return SAEnum(e, native_enum=False, length=length, validate_strings=True)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(_enum(Role), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    student: Mapped[Student | None] = relationship(back_populates="user", uselist=False)
    teacher: Mapped[Teacher | None] = relationship(back_populates="user", uselist=False)
    guardian: Mapped[Guardian | None] = relationship(back_populates="user", uselist=False)

class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True)
    admission_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    dob: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(16))
    address: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user: Mapped[User | None] = relationship(back_populates="student")
    enrollments: Mapped[list[Enrollment]] = relationship(back_populates="student", cascade="all, delete-orphan")
    invoices: Mapped[list[Invoice]] = relationship(back_populates="student", cascade="all, delete-orphan")
    guardian_links: Mapped[list[GuardianStudent]] = relationship(back_populates="student", cascade="all, delete-orphan")
    @property
    def full_name(self) -> str: return f"{self.first_name} {self.last_name}"

class Teacher(Base):
    __tablename__ = "teachers"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True)
    employee_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(32))
    hire_date: Mapped[date | None] = mapped_column(Date)
    user: Mapped[User | None] = relationship(back_populates="teacher")
    assignments: Mapped[list[TeachingAssignment]] = relationship(back_populates="teacher", cascade="all, delete-orphan")
    @property
    def full_name(self) -> str: return f"{self.first_name} {self.last_name}"

class Guardian(Base):
    __tablename__ = "guardians"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True)
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    user: Mapped[User | None] = relationship(back_populates="guardian")
    links: Mapped[list[GuardianStudent]] = relationship(back_populates="guardian", cascade="all, delete-orphan")

class GuardianStudent(Base):
    __tablename__ = "guardian_students"
    guardian_id: Mapped[int] = mapped_column(ForeignKey("guardians.id", ondelete="CASCADE"), primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), primary_key=True)
    relationship: Mapped[str | None] = mapped_column(String(32))
    guardian: Mapped[Guardian] = relationship(back_populates="links")
    student: Mapped[Student] = relationship(back_populates="guardian_links")

class AcademicYear(Base):
    __tablename__ = "academic_years"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    terms: Mapped[list[Term]] = relationship(back_populates="academic_year", cascade="all, delete-orphan")

class Term(Base):
    __tablename__ = "terms"
    __table_args__ = (UniqueConstraint("academic_year_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(32))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    academic_year: Mapped[AcademicYear] = relationship(back_populates="terms")

class ClassRoom(Base):
    __tablename__ = "classrooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    level: Mapped[int] = mapped_column(default=0)
    sections: Mapped[list[Section]] = relationship(back_populates="classroom")

class Section(Base):
    __tablename__ = "sections"
    __table_args__ = (UniqueConstraint("classroom_id", "academic_year_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    classroom_id: Mapped[int] = mapped_column(ForeignKey("classrooms.id", ondelete="CASCADE"), index=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(16))
    capacity: Mapped[int] = mapped_column(default=40)
    classroom: Mapped[ClassRoom] = relationship(back_populates="sections")
    academic_year: Mapped[AcademicYear] = relationship()
    enrollments: Mapped[list[Enrollment]] = relationship(back_populates="section", cascade="all, delete-orphan")
    teaching_assignments: Mapped[list[TeachingAssignment]] = relationship(back_populates="section", cascade="all, delete-orphan")
    timetable: Mapped[list[TimetableEntry]] = relationship(back_populates="section", cascade="all, delete-orphan")

class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(128))

class TeachingAssignment(Base):
    __tablename__ = "teaching_assignments"
    __table_args__ = (UniqueConstraint("teacher_id", "subject_id", "section_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id", ondelete="CASCADE"), index=True)
    teacher: Mapped[Teacher] = relationship(back_populates="assignments")
    subject: Mapped[Subject] = relationship()
    section: Mapped[Section] = relationship(back_populates="teaching_assignments")

class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("student_id", "section_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id", ondelete="CASCADE"), index=True)
    roll_no: Mapped[int | None] = mapped_column()
    enrolled_on: Mapped[date] = mapped_column(Date, default=date.today)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    student: Mapped[Student] = relationship(back_populates="enrollments")
    section: Mapped[Section] = relationship(back_populates="enrollments")
    attendance: Mapped[list[AttendanceRecord]] = relationship(back_populates="enrollment", cascade="all, delete-orphan")
    scores: Mapped[list[Score]] = relationship(back_populates="enrollment", cascade="all, delete-orphan")

class TimetableEntry(Base):
    __tablename__ = "timetable_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"))
    day_of_week: Mapped[int] = mapped_column()
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    room: Mapped[str | None] = mapped_column(String(32))
    section: Mapped[Section] = relationship(back_populates="timetable")
    subject: Mapped[Subject] = relationship()
    teacher: Mapped[Teacher] = relationship()

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("enrollment_id", "date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(_enum(AttendanceStatus))
    note: Mapped[str | None] = mapped_column(String(255))
    marked_by_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id", ondelete="SET NULL"))
    marked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    enrollment: Mapped[Enrollment] = relationship(back_populates="attendance")

class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id", ondelete="CASCADE"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"), index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(255))
    type: Mapped[AssessmentType] = mapped_column(_enum(AssessmentType))
    max_score: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    due_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    section: Mapped[Section] = relationship()
    subject: Mapped[Subject] = relationship()
    term: Mapped[Term] = relationship()
    scores: Mapped[list[Score]] = relationship(back_populates="assessment", cascade="all, delete-orphan")

class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (UniqueConstraint("assessment_id", "enrollment_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id", ondelete="CASCADE"), index=True)
    score: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    comment: Mapped[str | None] = mapped_column(String(255))
    graded_by_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id", ondelete="SET NULL"))
    graded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    assessment: Mapped[Assessment] = relationship(back_populates="scores")
    enrollment: Mapped[Enrollment] = relationship(back_populates="scores")

class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    term_id: Mapped[int | None] = mapped_column(ForeignKey("terms.id", ondelete="SET NULL"), index=True)
    description: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[InvoiceStatus] = mapped_column(_enum(InvoiceStatus), default=InvoiceStatus.unpaid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    student: Mapped[Student] = relationship(back_populates="invoices")
    payments: Mapped[list[Payment]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    @property
    def paid(self) -> Decimal: return sum((p.amount for p in self.payments), Decimal("0.00"))
    @property
    def balance(self) -> Decimal: return self.amount - self.paid

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    method: Mapped[str] = mapped_column(String(32))
    reference: Mapped[str | None] = mapped_column(String(128))
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    invoice: Mapped[Invoice] = relationship(back_populates="payments")

class Announcement(Base):
    __tablename__ = "announcements"
    id: Mapped[int] = mapped_column(primary_key=True)
    author_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    audience: Mapped[Audience] = mapped_column(_enum(Audience), default=Audience.all)
    section_id: Mapped[int | None] = mapped_column(ForeignKey("sections.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
'''

FILES["app/security.py"] = r'''from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from app.config import get_settings

settings = get_settings()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed.encode())
    except ValueError:
        return False

def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "role": role, "iat": now, "exp": now + timedelta(minutes=settings.access_token_minutes)}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
'''

FILES["app/deps.py"] = r'''from collections.abc import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Enrollment, GuardianStudent, Role, Student, Teacher, TeachingAssignment, User
from app.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
CREDENTIALS_ERROR = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    import jwt as pyjwt
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except (pyjwt.PyJWTError, KeyError, ValueError):
        raise CREDENTIALS_ERROR
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise CREDENTIALS_ERROR
    return user

def require_roles(*roles: Role) -> Callable[..., User]:
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user
    return checker

def teacher_teaches_section(db: Session, teacher_id: int, section_id: int) -> bool:
    return db.scalar(select(TeachingAssignment.id).where(TeachingAssignment.teacher_id == teacher_id, TeachingAssignment.section_id == section_id)) is not None

def active_enrollment(db: Session, student_id: int, section_id: int) -> Enrollment | None:
    return db.scalar(select(Enrollment).where(Enrollment.student_id == student_id, Enrollment.section_id == section_id, Enrollment.is_active.is_(True)))

def assert_section_access(db: Session, user: User, section_id: int) -> None:
    if user.role == Role.admin: return
    if user.role == Role.teacher and user.teacher:
        if teacher_teaches_section(db, user.teacher.id, section_id): return
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not assigned to this section")
    if user.role == Role.student and user.student:
        if active_enrollment(db, user.student.id, section_id): return
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not enrolled in this section")
    if user.role == Role.guardian and user.guardian:
        child_ids = db.scalars(select(GuardianStudent.student_id).where(GuardianStudent.guardian_id == user.guardian.id)).all()
        if any(active_enrollment(db, sid, section_id) for sid in child_ids): return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")

def active_enrollment_any(db: Session, student_id: int, section_ids: list[int]) -> bool:
    return db.scalar(select(Enrollment.id).where(Enrollment.student_id == student_id, Enrollment.section_id.in_(section_ids), Enrollment.is_active.is_(True))) is not None

def assert_student_access(db: Session, user: User, student_id: int) -> None:
    if user.role == Role.admin: return
    if user.role == Role.teacher and user.teacher:
        section_ids = db.scalars(select(TeachingAssignment.section_id).where(TeachingAssignment.teacher_id == user.teacher.id)).all()
        if section_ids and active_enrollment_any(db, student_id, list(section_ids)): return
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your student")
    if user.role == Role.student and user.student and user.student.id == student_id: return
    if user.role == Role.guardian and user.guardian:
        link = db.scalar(select(GuardianStudent).where(GuardianStudent.guardian_id == user.guardian.id, GuardianStudent.student_id == student_id))
        if link: return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
'''

FILES["app/schemas.py"] = r'''from datetime import date, datetime, time
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models import AssessmentType, AttendanceStatus, Audience, InvoiceStatus, Role

class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class UserOut(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class StudentCreate(BaseModel):
    admission_no: str
    first_name: str
    last_name: str
    dob: date | None = None
    gender: str | None = None
    address: str | None = None
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)

class StudentUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    dob: date | None = None
    gender: str | None = None
    address: str | None = None

class StudentOut(ORMModel):
    id: int
    admission_no: str
    first_name: str
    last_name: str
    full_name: str
    dob: date | None
    gender: str | None
    address: str | None

class TeacherCreate(BaseModel):
    employee_no: str
    first_name: str
    last_name: str
    phone: str | None = None
    hire_date: date | None = None
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)

class TeacherOut(ORMModel):
    id: int
    employee_no: str
    first_name: str
    last_name: str
    full_name: str
    phone: str | None

class AcademicYearCreate(BaseModel):
    name: str
    start_date: date
    end_date: date
    is_current: bool = False

class AcademicYearOut(ORMModel):
    id: int
    name: str
    start_date: date
    end_date: date
    is_current: bool

class TermCreate(BaseModel):
    academic_year_id: int
    name: str
    start_date: date
    end_date: date

class TermOut(ORMModel):
    id: int
    academic_year_id: int
    name: str
    start_date: date
    end_date: date

class ClassRoomCreate(BaseModel):
    name: str
    level: int = 0

class ClassRoomOut(ORMModel):
    id: int
    name: str
    level: int

class SectionCreate(BaseModel):
    classroom_id: int
    academic_year_id: int
    name: str
    capacity: int = 40

class SectionOut(ORMModel):
    id: int
    classroom_id: int
    academic_year_id: int
    name: str
    capacity: int

class SubjectCreate(BaseModel):
    code: str
    name: str

class SubjectOut(ORMModel):
    id: int
    code: str
    name: str

class EnrollmentCreate(BaseModel):
    student_id: int
    section_id: int
    roll_no: int | None = None

class EnrollmentOut(ORMModel):
    id: int
    student_id: int
    section_id: int
    roll_no: int | None
    is_active: bool

class TeachingAssignmentCreate(BaseModel):
    teacher_id: int
    subject_id: int
    section_id: int

class TeachingAssignmentOut(ORMModel):
    id: int
    teacher_id: int
    subject_id: int
    section_id: int

class TimetableCreate(BaseModel):
    section_id: int
    subject_id: int
    teacher_id: int
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    room: str | None = None

class TimetableOut(ORMModel):
    id: int
    section_id: int
    subject_id: int
    teacher_id: int
    day_of_week: int
    start_time: time
    end_time: time
    room: str | None

class AttendanceItem(BaseModel):
    student_id: int
    status: AttendanceStatus
    note: str | None = None

class AttendanceBulkIn(BaseModel):
    section_id: int
    date: date
    records: list[AttendanceItem]

class AttendanceOut(ORMModel):
    id: int
    enrollment_id: int
    date: date
    status: AttendanceStatus
    note: str | None

class AssessmentCreate(BaseModel):
    section_id: int
    subject_id: int
    term_id: int
    title: str
    type: AssessmentType
    max_score: Decimal = Field(gt=0)
    due_date: date | None = None

class AssessmentOut(ORMModel):
    id: int
    section_id: int
    subject_id: int
    term_id: int
    title: str
    type: AssessmentType
    max_score: Decimal
    due_date: date | None

class ScoreItem(BaseModel):
    student_id: int
    score: Decimal = Field(ge=0)
    comment: str | None = None

class ScoreBulkIn(BaseModel):
    records: list[ScoreItem]

class ScoreLine(BaseModel):
    assessment_id: int
    title: str
    type: AssessmentType
    score: Decimal | None
    max_score: Decimal
    comment: str | None = None

class SubjectResult(BaseModel):
    subject_id: int
    subject_name: str
    lines: list[ScoreLine]
    total_scored: Decimal
    total_possible: Decimal
    percentage: float

class ReportCard(BaseModel):
    student_id: int
    student_name: str
    term_id: int
    term_name: str
    subjects: list[SubjectResult]
    overall_percentage: float

class InvoiceCreate(BaseModel):
    student_id: int
    term_id: int | None = None
    description: str
    amount: Decimal = Field(gt=0)
    due_date: date

class InvoiceOut(ORMModel):
    id: int
    student_id: int
    term_id: int | None
    description: str
    amount: Decimal
    due_date: date
    status: InvoiceStatus
    paid: Decimal
    balance: Decimal

class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    method: str
    reference: str | None = None

class PaymentOut(ORMModel):
    id: int
    invoice_id: int
    amount: Decimal
    method: str
    reference: str | None
    paid_at: datetime

class AnnouncementCreate(BaseModel):
    title: str
    body: str
    audience: Audience = Audience.all
    section_id: int | None = None

class AnnouncementOut(ORMModel):
    id: int
    author_user_id: int
    title: str
    body: str
    audience: Audience
    section_id: int | None
    created_at: datetime
'''

if __name__ == "__main__":
    for path, content in FILES.items():
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        print(f"wrote {path}")
    print("\nDone. Now run: python bootstrap2.py")