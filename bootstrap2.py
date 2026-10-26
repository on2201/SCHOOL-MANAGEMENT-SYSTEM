from pathlib import Path

FILES = {}

FILES["app/routers/auth.py"] = r'''from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import Token, UserOut
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not user.is_active or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    return Token(access_token=create_access_token(user.id, user.role.value))

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
'''

FILES["app/routers/academics.py"] = r'''from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import assert_section_access, require_roles
from app.models import AcademicYear, ClassRoom, Enrollment, Role, Section, Student, Subject, Teacher, TeachingAssignment, Term, TimetableEntry, User
from app.schemas import AcademicYearCreate, AcademicYearOut, ClassRoomCreate, ClassRoomOut, EnrollmentCreate, EnrollmentOut, SectionCreate, SectionOut, StudentCreate, StudentOut, StudentUpdate, SubjectCreate, SubjectOut, TeacherCreate, TeacherOut, TeachingAssignmentCreate, TeachingAssignmentOut, TermCreate, TermOut, TimetableCreate, TimetableOut
from app.security import hash_password

router = APIRouter(tags=["academics"])
admin_only = require_roles(Role.admin)
staff = require_roles(Role.admin, Role.teacher)

@router.post("/academic-years", response_model=AcademicYearOut, status_code=201)
def create_year(payload: AcademicYearCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    if payload.is_current: db.execute(AcademicYear.__table__.update().values(is_current=False))
    year = AcademicYear(**payload.model_dump()); db.add(year); db.commit(); return year

@router.get("/academic-years", response_model=list[AcademicYearOut])
def list_years(db: Session = Depends(get_db), _: User = Depends(staff)):
    return db.scalars(select(AcademicYear).order_by(AcademicYear.start_date.desc())).all()

@router.post("/terms", response_model=TermOut, status_code=201)
def create_term(payload: TermCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    if not db.get(AcademicYear, payload.academic_year_id): raise HTTPException(404, "Academic year not found")
    term = Term(**payload.model_dump()); db.add(term); db.commit(); return term

@router.get("/terms", response_model=list[TermOut])
def list_terms(academic_year_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(staff)):
    q = select(Term).order_by(Term.start_date)
    if academic_year_id: q = q.where(Term.academic_year_id == academic_year_id)
    return db.scalars(q).all()

@router.post("/classrooms", response_model=ClassRoomOut, status_code=201)
def create_classroom(payload: ClassRoomCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    room = ClassRoom(**payload.model_dump()); db.add(room); db.commit(); return room

@router.get("/classrooms", response_model=list[ClassRoomOut])
def list_classrooms(db: Session = Depends(get_db), _: User = Depends(staff)):
    return db.scalars(select(ClassRoom).order_by(ClassRoom.level)).all()

@router.post("/sections", response_model=SectionOut, status_code=201)
def create_section(payload: SectionCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    if not db.get(ClassRoom, payload.classroom_id): raise HTTPException(404, "Classroom not found")
    if not db.get(AcademicYear, payload.academic_year_id): raise HTTPException(404, "Academic year not found")
    section = Section(**payload.model_dump()); db.add(section); db.commit(); return section

@router.get("/sections", response_model=list[SectionOut])
def list_sections(academic_year_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(staff)):
    q = select(Section).order_by(Section.classroom_id, Section.name)
    if academic_year_id: q = q.where(Section.academic_year_id == academic_year_id)
    return db.scalars(q).all()

@router.post("/subjects", response_model=SubjectOut, status_code=201)
def create_subject(payload: SubjectCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    subject = Subject(**payload.model_dump()); db.add(subject); db.commit(); return subject

@router.get("/subjects", response_model=list[SubjectOut])
def list_subjects(db: Session = Depends(get_db), _: User = Depends(staff)):
    return db.scalars(select(Subject).order_by(Subject.name)).all()

@router.post("/teachers", response_model=TeacherOut, status_code=201)
def create_teacher(payload: TeacherCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    data = payload.model_dump(exclude={"email", "password"}); teacher = Teacher(**data)
    if payload.email:
        if not payload.password: raise HTTPException(422, "password is required when email is provided")
        email = payload.email.lower()
        if db.scalar(select(User).where(User.email == email)): raise HTTPException(409, "Email already registered")
        teacher.user = User(email=email, full_name=f"{payload.first_name} {payload.last_name}", role=Role.teacher, hashed_password=hash_password(payload.password))
    db.add(teacher); db.commit(); return teacher

@router.get("/teachers", response_model=list[TeacherOut])
def list_teachers(db: Session = Depends(get_db), _: User = Depends(staff)):
    return db.scalars(select(Teacher).order_by(Teacher.last_name)).all()

@router.post("/students", response_model=StudentOut, status_code=201)
def create_student(payload: StudentCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    data = payload.model_dump(exclude={"email", "password"}); student = Student(**data)
    if payload.email:
        if not payload.password: raise HTTPException(422, "password is required when email is provided")
        email = payload.email.lower()
        if db.scalar(select(User).where(User.email == email)): raise HTTPException(409, "Email already registered")
        student.user = User(email=email, full_name=f"{payload.first_name} {payload.last_name}", role=Role.student, hashed_password=hash_password(payload.password))
    db.add(student); db.commit(); return student

@router.get("/students", response_model=list[StudentOut])
def list_students(q: str | None = Query(default=None), limit: int = Query(default=50, le=200), offset: int = 0, db: Session = Depends(get_db), _: User = Depends(staff)):
    stmt = select(Student).order_by(Student.last_name, Student.first_name)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(Student.first_name).like(like) | func.lower(Student.last_name).like(like) | func.lower(Student.admission_no).like(like))
    return db.scalars(stmt.limit(limit).offset(offset)).all()

@router.get("/students/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: Session = Depends(get_db), _: User = Depends(staff)):
    student = db.get(Student, student_id)
    if not student: raise HTTPException(404, "Student not found")
    return student

@router.patch("/students/{student_id}", response_model=StudentOut)
def update_student(student_id: int, payload: StudentUpdate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    student = db.get(Student, student_id)
    if not student: raise HTTPException(404, "Student not found")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(student, key, value)
    db.commit(); return student

@router.post("/enrollments", response_model=EnrollmentOut, status_code=201)
def enroll(payload: EnrollmentCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    student = db.get(Student, payload.student_id); section = db.get(Section, payload.section_id)
    if not student or not section: raise HTTPException(404, "Student or section not found")
    clash = db.scalar(select(Enrollment).join(Section, Section.id == Enrollment.section_id).where(Enrollment.student_id == student.id, Enrollment.is_active.is_(True), Section.academic_year_id == section.academic_year_id))
    if clash: raise HTTPException(409, "Student already enrolled in this academic year")
    count = db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.section_id == section.id, Enrollment.is_active.is_(True)))
    if count >= section.capacity: raise HTTPException(409, "Section is at capacity")
    enrollment = Enrollment(**payload.model_dump()); db.add(enrollment); db.commit(); return enrollment

@router.get("/sections/{section_id}/students", response_model=list[StudentOut])
def section_roster(section_id: int, db: Session = Depends(get_db), user: User = Depends(staff)):
    assert_section_access(db, user, section_id)
    return db.scalars(select(Student).join(Enrollment, Enrollment.student_id == Student.id).where(Enrollment.section_id == section_id, Enrollment.is_active.is_(True)).order_by(Enrollment.roll_no, Student.last_name)).all()

@router.post("/teaching-assignments", response_model=TeachingAssignmentOut, status_code=201)
def assign_teacher(payload: TeachingAssignmentCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    for model, key in ((Teacher, payload.teacher_id), (Subject, payload.subject_id), (Section, payload.section_id)):
        if not db.get(model, key): raise HTTPException(404, f"{model.__name__} not found")
    ta = TeachingAssignment(**payload.model_dump()); db.add(ta); db.commit(); return ta

@router.get("/sections/{section_id}/teaching-assignments", response_model=list[TeachingAssignmentOut])
def list_section_assignments(section_id: int, db: Session = Depends(get_db), user: User = Depends(staff)):
    assert_section_access(db, user, section_id)
    return db.scalars(select(TeachingAssignment).where(TeachingAssignment.section_id == section_id)).all()

@router.post("/timetable", response_model=TimetableOut, status_code=201)
def add_timetable_entry(payload: TimetableCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    if payload.end_time <= payload.start_time: raise HTTPException(422, "end_time must be after start_time")
    existing = db.scalars(select(TimetableEntry).where(TimetableEntry.day_of_week == payload.day_of_week, ((TimetableEntry.section_id == payload.section_id) | (TimetableEntry.teacher_id == payload.teacher_id)))).all()
    for e in existing:
        if payload.start_time < e.end_time and e.start_time < payload.end_time: raise HTTPException(409, "Timetable conflict with an existing entry")
    entry = TimetableEntry(**payload.model_dump()); db.add(entry); db.commit(); return entry

@router.get("/sections/{section_id}/timetable", response_model=list[TimetableOut])
def section_timetable(section_id: int, db: Session = Depends(get_db), user: User = Depends(staff)):
    assert_section_access(db, user, section_id)
    return db.scalars(select(TimetableEntry).where(TimetableEntry.section_id == section_id).order_by(TimetableEntry.day_of_week, TimetableEntry.start_time)).all()
'''

FILES["app/routers/attendance.py"] = r'''from datetime import date as date_type
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import assert_section_access, assert_student_access, require_roles, teacher_teaches_section
from app.models import AttendanceRecord, AttendanceStatus, Enrollment, Role, User
from app.schemas import AttendanceBulkIn, AttendanceOut

router = APIRouter(prefix="/attendance", tags=["attendance"])
marker = require_roles(Role.admin, Role.teacher)

@router.post("/bulk", response_model=list[AttendanceOut])
def mark_attendance(payload: AttendanceBulkIn, db: Session = Depends(get_db), user: User = Depends(marker)):
    assert_section_access(db, user, payload.section_id)
    if user.role == Role.teacher and not teacher_teaches_section(db, user.teacher.id, payload.section_id): raise HTTPException(403, "Not assigned to this section")
    enrollments = {e.student_id: e for e in db.scalars(select(Enrollment).where(Enrollment.section_id == payload.section_id, Enrollment.is_active.is_(True))).all()}
    out: list[AttendanceRecord] = []
    for item in payload.records:
        enrollment = enrollments.get(item.student_id)
        if not enrollment: raise HTTPException(422, f"Student {item.student_id} is not enrolled in this section")
        record = db.scalar(select(AttendanceRecord).where(AttendanceRecord.enrollment_id == enrollment.id, AttendanceRecord.date == payload.date))
        if record:
            record.status = item.status; record.note = item.note; record.marked_by_id = user.teacher.id if user.teacher else None
        else:
            record = AttendanceRecord(enrollment_id=enrollment.id, date=payload.date, status=item.status, note=item.note, marked_by_id=user.teacher.id if user.teacher else None)
            db.add(record)
        out.append(record)
    db.commit(); return out

@router.get("/section/{section_id}", response_model=list[AttendanceOut])
def section_attendance(section_id: int, on: date_type = Query(alias="date"), db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.teacher))):
    assert_section_access(db, user, section_id)
    return db.scalars(select(AttendanceRecord).join(Enrollment, Enrollment.id == AttendanceRecord.enrollment_id).where(Enrollment.section_id == section_id, AttendanceRecord.date == on)).all()

@router.get("/student/{student_id}", response_model=list[AttendanceOut])
def student_attendance(student_id: int, date_from: date_type | None = None, date_to: date_type | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.teacher, Role.student, Role.guardian))):
    assert_student_access(db, user, student_id)
    q = select(AttendanceRecord).join(Enrollment, Enrollment.id == AttendanceRecord.enrollment_id).where(Enrollment.student_id == student_id).order_by(AttendanceRecord.date.desc())
    if date_from: q = q.where(AttendanceRecord.date >= date_from)
    if date_to: q = q.where(AttendanceRecord.date <= date_to)
    return db.scalars(q).all()

@router.get("/student/{student_id}/summary")
def attendance_summary(student_id: int, date_from: date_type | None = None, date_to: date_type | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.teacher, Role.student, Role.guardian))):
    assert_student_access(db, user, student_id)
    q = select(AttendanceRecord).join(Enrollment, Enrollment.id == AttendanceRecord.enrollment_id).where(Enrollment.student_id == student_id)
    if date_from: q = q.where(AttendanceRecord.date >= date_from)
    if date_to: q = q.where(AttendanceRecord.date <= date_to)
    records = db.scalars(q).all()
    counts = {s.value: 0 for s in AttendanceStatus}
    for r in records: counts[r.status.value] += 1
    total = len(records); present_equiv = counts["present"] + counts["late"]
    return {"student_id": student_id, "total_days": total, "counts": counts, "attendance_rate": round(present_equiv / total * 100, 2) if total else 0.0}
'''

FILES["app/routers/assessments.py"] = r'''from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import active_enrollment, assert_section_access, assert_student_access, require_roles, teacher_teaches_section
from app.models import Assessment, Enrollment, Role, Score, Student, Subject, Term, User
from app.schemas import AssessmentCreate, AssessmentOut, ReportCard, ScoreBulkIn, ScoreLine, SubjectResult

router = APIRouter(prefix="/assessments", tags=["assessments"])
author = require_roles(Role.admin, Role.teacher)
reader = require_roles(Role.admin, Role.teacher, Role.student, Role.guardian)

@router.post("", response_model=AssessmentOut, status_code=201)
def create_assessment(payload: AssessmentCreate, db: Session = Depends(get_db), user: User = Depends(author)):
    assert_section_access(db, user, payload.section_id)
    if user.role == Role.teacher and not teacher_teaches_section(db, user.teacher.id, payload.section_id): raise HTTPException(403, "Not assigned to this section")
    if not db.get(Term, payload.term_id): raise HTTPException(404, "Term not found")
    assessment = Assessment(**payload.model_dump(), created_by_id=user.teacher.id if user.teacher else None)
    db.add(assessment); db.commit(); return assessment

@router.get("", response_model=list[AssessmentOut])
def list_assessments(section_id: int | None = None, term_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(reader)):
    if section_id: assert_section_access(db, user, section_id)
    q = select(Assessment).order_by(Assessment.due_date)
    if section_id: q = q.where(Assessment.section_id == section_id)
    if term_id: q = q.where(Assessment.term_id == term_id)
    return db.scalars(q).all()

@router.post("/{assessment_id}/scores")
def enter_scores(assessment_id: int, payload: ScoreBulkIn, db: Session = Depends(get_db), user: User = Depends(author)):
    assessment = db.get(Assessment, assessment_id)
    if not assessment: raise HTTPException(404, "Assessment not found")
    assert_section_access(db, user, assessment.section_id)
    if user.role == Role.teacher and not teacher_teaches_section(db, user.teacher.id, assessment.section_id): raise HTTPException(403, "Not assigned to this section")
    saved = 0
    for item in payload.records:
        if item.score > assessment.max_score: raise HTTPException(422, f"Score {item.score} exceeds max_score {assessment.max_score} for student {item.student_id}")
        enrollment = active_enrollment(db, item.student_id, assessment.section_id)
        if not enrollment: raise HTTPException(422, f"Student {item.student_id} is not enrolled in this section")
        row = db.scalar(select(Score).where(Score.assessment_id == assessment.id, Score.enrollment_id == enrollment.id))
        if row:
            row.score = item.score; row.comment = item.comment; row.graded_by_id = user.teacher.id if user.teacher else None
        else:
            db.add(Score(assessment_id=assessment.id, enrollment_id=enrollment.id, score=item.score, comment=item.comment, graded_by_id=user.teacher.id if user.teacher else None))
        saved += 1
    db.commit(); return {"saved": saved}

@router.get("/students/{student_id}/report", response_model=ReportCard)
def report_card(student_id: int, term_id: int, db: Session = Depends(get_db), user: User = Depends(reader)):
    assert_student_access(db, user, student_id)
    student = db.get(Student, student_id); term = db.get(Term, term_id)
    if not student or not term: raise HTTPException(404, "Student or term not found")
    enrollment = db.scalar(select(Enrollment).where(Enrollment.student_id == student_id, Enrollment.is_active.is_(True)).order_by(Enrollment.enrolled_on.desc()).limit(1))
    if not enrollment:
        return ReportCard(student_id=student_id, student_name=student.full_name, term_id=term_id, term_name=term.name, subjects=[], overall_percentage=0.0)
    rows = db.execute(select(Assessment, Subject, Score).join(Subject, Subject.id == Assessment.subject_id).outerjoin(Score, and_(Score.assessment_id == Assessment.id, Score.enrollment_id == enrollment.id)).where(Assessment.section_id == enrollment.section_id, Assessment.term_id == term_id).order_by(Subject.name, Assessment.due_date)).all()
    grouped: dict[int, SubjectResult] = {}
    for assessment, subject, score in rows:
        bucket = grouped.setdefault(subject.id, SubjectResult(subject_id=subject.id, subject_name=subject.name, lines=[], total_scored=Decimal("0.00"), total_possible=Decimal("0.00"), percentage=0.0))
        bucket.lines.append(ScoreLine(assessment_id=assessment.id, title=assessment.title, type=assessment.type, score=score.score if score else None, max_score=assessment.max_score, comment=score.comment if score else None))
        if score: bucket.total_scored += score.score
        bucket.total_possible += assessment.max_score
    subjects: list[SubjectResult] = []; scored_total = Decimal("0.00"); possible_total = Decimal("0.00")
    for bucket in grouped.values():
        bucket.percentage = float(bucket.total_scored / bucket.total_possible * 100) if bucket.total_possible else 0.0
        scored_total += bucket.total_scored; possible_total += bucket.total_possible; subjects.append(bucket)
    return ReportCard(student_id=student.id, student_name=student.full_name, term_id=term.id, term_name=term.name, subjects=subjects, overall_percentage=float(scored_total / possible_total * 100) if possible_total else 0.0)
'''

FILES["app/routers/finance.py"] = r'''from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import assert_student_access, require_roles
from app.models import Invoice, InvoiceStatus, Payment, Role, Student, User
from app.schemas import InvoiceCreate, InvoiceOut, PaymentCreate, PaymentOut

router = APIRouter(prefix="/finance", tags=["finance"])
admin_only = require_roles(Role.admin)

@router.post("/invoices", response_model=InvoiceOut, status_code=201)
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    if not db.get(Student, payload.student_id): raise HTTPException(404, "Student not found")
    invoice = Invoice(**payload.model_dump(), status=InvoiceStatus.unpaid); db.add(invoice); db.commit(); return invoice

@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(student_id: int | None = None, status: InvoiceStatus | None = None, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.student, Role.guardian))):
    q = select(Invoice).order_by(Invoice.due_date.desc())
    if user.role in (Role.student, Role.guardian):
        if student_id is None: raise HTTPException(422, "student_id is required for this role")
        assert_student_access(db, user, student_id); q = q.where(Invoice.student_id == student_id)
    elif student_id: q = q.where(Invoice.student_id == student_id)
    if status: q = q.where(Invoice.status == status)
    return db.scalars(q).all()

@router.post("/invoices/{invoice_id}/payments", response_model=PaymentOut, status_code=201)
def record_payment(invoice_id: int, payload: PaymentCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice: raise HTTPException(404, "Invoice not found")
    if invoice.status == InvoiceStatus.void: raise HTTPException(409, "Invoice is void")
    if payload.amount > invoice.balance: raise HTTPException(422, f"Payment exceeds outstanding balance of {invoice.balance}")
    payment = Payment(invoice_id=invoice.id, **payload.model_dump()); db.add(payment); db.flush()
    total_paid = invoice.paid
    if total_paid >= invoice.amount: invoice.status = InvoiceStatus.paid
    elif total_paid > Decimal("0.00"): invoice.status = InvoiceStatus.partial
    db.commit(); return payment
'''

FILES["app/routers/announcements.py"] = r'''from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models import Announcement, Audience, Enrollment, GuardianStudent, Role, TeachingAssignment, User
from app.schemas import AnnouncementCreate, AnnouncementOut

router = APIRouter(prefix="/announcements", tags=["announcements"])

@router.post("", response_model=AnnouncementOut, status_code=201)
def create_announcement(payload: AnnouncementCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(Role.admin, Role.teacher))):
    if payload.audience == Audience.section and payload.section_id is None: raise HTTPException(422, "section_id is required for section announcements")
    ann = Announcement(author_user_id=user.id, **payload.model_dump()); db.add(ann); db.commit(); return ann

@router.get("", response_model=list[AnnouncementOut])
def list_announcements(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == Role.admin: return db.scalars(select(Announcement).order_by(Announcement.created_at.desc())).all()
    audiences = [Audience.all]; section_ids: list[int] = []
    if user.role == Role.teacher and user.teacher:
        audiences.append(Audience.teachers)
        section_ids = db.scalars(select(TeachingAssignment.section_id).where(TeachingAssignment.teacher_id == user.teacher.id)).all()
    elif user.role == Role.student and user.student:
        audiences.append(Audience.students)
        section_ids = db.scalars(select(Enrollment.section_id).where(Enrollment.student_id == user.student.id, Enrollment.is_active.is_(True))).all()
    elif user.role == Role.guardian and user.guardian:
        audiences.append(Audience.guardians)
        child_ids = db.scalars(select(GuardianStudent.student_id).where(GuardianStudent.guardian_id == user.guardian.id)).all()
        if child_ids: section_ids = db.scalars(select(Enrollment.section_id).where(Enrollment.student_id.in_(child_ids), Enrollment.is_active.is_(True))).all()
    stmt = select(Announcement).where(Announcement.audience.in_(audiences))
    if section_ids: stmt = stmt.union(select(Announcement).where(Announcement.audience == Audience.section, Announcement.section_id.in_(section_ids)))
    return db.scalars(stmt.order_by(Announcement.created_at.desc())).all()
'''

FILES["app/main.py"] = r'''from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import init_db
from app.routers import academics, announcements, assessments, attendance, auth, finance

settings = get_settings()

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield

app = FastAPI(title="School Management System", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(academics.router)
app.include_router(attendance.router)
app.include_router(assessments.router)
app.include_router(finance.router)
app.include_router(announcements.router)

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
'''

FILES["seed.py"] = r'''"""Idempotent dev seed. Run: python seed.py"""
from datetime import date, time
from sqlalchemy import select
from app.database import SessionLocal, init_db
from app.models import AcademicYear, ClassRoom, Enrollment, Role, Section, Student, Subject, Teacher, TeachingAssignment, Term, TimetableEntry, User
from app.security import hash_password

def get_or_create(db, model, defaults=None, **filters):
    obj = db.scalar(select(model).filter_by(**filters))
    if obj: return obj
    obj = model(**{**filters, **(defaults or {})}); db.add(obj); db.flush(); return obj

def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        get_or_create(db, User, email="admin@school.test", defaults=dict(full_name="System Admin", role=Role.admin, hashed_password=hash_password("AdminPass123")))
        year = get_or_create(db, AcademicYear, name="2025-2026", defaults=dict(start_date=date(2025, 9, 1), end_date=date(2026, 6, 30), is_current=True))
        get_or_create(db, Term, academic_year_id=year.id, name="Term 1", defaults=dict(start_date=date(2025, 9, 1), end_date=date(2025, 12, 15)))
        grade5 = get_or_create(db, ClassRoom, name="Grade 5", defaults=dict(level=5))
        section_a = get_or_create(db, Section, classroom_id=grade5.id, academic_year_id=year.id, name="A", defaults=dict(capacity=40))
        math = get_or_create(db, Subject, code="MATH", defaults=dict(name="Mathematics"))
        get_or_create(db, Subject, code="ENG", defaults=dict(name="English"))
        teacher_user = get_or_create(db, User, email="teacher@school.test", defaults=dict(full_name="Jane Doe", role=Role.teacher, hashed_password=hash_password("TeacherPass123")))
        teacher = get_or_create(db, Teacher, employee_no="EMP-001", defaults=dict(first_name="Jane", last_name="Doe", user_id=teacher_user.id))
        get_or_create(db, TeachingAssignment, teacher_id=teacher.id, subject_id=math.id, section_id=section_a.id)
        get_or_create(db, TimetableEntry, section_id=section_a.id, subject_id=math.id, teacher_id=teacher.id, day_of_week=0, start_time=time(9, 0), defaults=dict(end_time=time(10, 0), room="R1"))
        for i in range(1, 6):
            student_user = get_or_create(db, User, email=f"student{i}@school.test", defaults=dict(full_name=f"Student {i}", role=Role.student, hashed_password=hash_password("StudentPass123")))
            student = get_or_create(db, Student, admission_no=f"ADM-{i:04d}", defaults=dict(first_name="Student", last_name=str(i), user_id=student_user.id))
            get_or_create(db, Enrollment, student_id=student.id, section_id=section_a.id, defaults=dict(roll_no=i, enrolled_on=date(2025, 9, 1)))
        db.commit()
        print("Seed complete.\n  admin@school.test / AdminPass123\n  teacher@school.test / TeacherPass123\n  student1@school.test / StudentPass123")
    finally:
        db.close()

if __name__ == "__main__":
    main()
'''

if __name__ == "__main__":
    for path, content in FILES.items():
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        print(f"wrote {path}")
    print("\nDone. All files generated.")