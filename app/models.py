from __future__ import annotations
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

    @property
    def student_id(self) -> int | None:
        return self.student.id if self.student else None

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
    relation_type: Mapped[str | None] = mapped_column(String(32))
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

class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id", ondelete="CASCADE"), index=True)
    file_url: Mapped[str] = mapped_column(String(512))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    grade: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    feedback: Mapped[str | None] = mapped_column(Text)
    assessment: Mapped[Assessment] = relationship()
    enrollment: Mapped[Enrollment] = relationship()

class PayrollRecord(Base):
    __tablename__ = "payroll_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), index=True)
    month: Mapped[int] = mapped_column()
    year: Mapped[int] = mapped_column()
    base_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    deductions: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    teacher: Mapped[Teacher] = relationship()