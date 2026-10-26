from datetime import date, datetime, time
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.models import AssessmentType, AttendanceStatus, Audience, InvoiceStatus, Role

class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool
    student_id: int | None = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class PasswordResetRequest(BaseModel):
    email: str
    new_password: str = Field(min_length=8)

class StudentCreate(BaseModel):
    admission_no: str
    first_name: str
    last_name: str
    dob: date | None = None
    gender: str | None = None
    address: str | None = None
    email: str | None = None
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
    email: str | None = None
    password: str | None = Field(default=None, min_length=8)

class TeacherUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None

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

class PayrollCreate(BaseModel):
    teacher_id: int
    month: int = Field(ge=1, le=12)
    year: int
    base_amount: Decimal = Field(gt=0)
    deductions: Decimal = Field(default=Decimal("0.00"), ge=0)

class PayrollOut(ORMModel):
    id: int
    teacher_id: int
    month: int
    year: int
    base_amount: Decimal
    deductions: Decimal
    net_amount: Decimal
    status: str
    paid_at: datetime | None

class SubmissionOut(ORMModel):
    id: int
    assessment_id: int
    enrollment_id: int
    file_url: str
    submitted_at: datetime
    grade: Decimal | None
    feedback: str | None