from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import assert_section_access, require_roles
from app.models import AcademicYear, ClassRoom, Enrollment, Role, Section, Student, Subject, Teacher, TeachingAssignment, Term, TimetableEntry, User
from app.schemas import (
    AcademicYearCreate, AcademicYearOut, ClassRoomCreate, ClassRoomOut, 
    EnrollmentCreate, EnrollmentOut, SectionCreate, SectionOut, 
    StudentCreate, StudentOut, StudentUpdate, SubjectCreate, SubjectOut, 
    TeacherCreate, TeacherOut, TeacherUpdate, TeachingAssignmentCreate, 
    TeachingAssignmentOut, TermCreate, TermOut, TimetableCreate, TimetableOut
)
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
    
    db.add(teacher)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Employee number already exists")
    return teacher

@router.get("/teachers", response_model=list[TeacherOut])
def list_teachers(db: Session = Depends(get_db), _: User = Depends(staff)):
    return db.scalars(select(Teacher).order_by(Teacher.last_name)).all()

@router.patch("/teachers/{teacher_id}", response_model=TeacherOut)
def update_teacher(teacher_id: int, payload: TeacherUpdate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    teacher = db.get(Teacher, teacher_id)
    if not teacher: raise HTTPException(404, "Teacher not found")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(teacher, key, value)
    db.commit(); return teacher

@router.delete("/teachers/{teacher_id}", status_code=204)
def delete_teacher(teacher_id: int, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    teacher = db.get(Teacher, teacher_id)
    if not teacher: raise HTTPException(404, "Teacher not found")
    if teacher.user: db.delete(teacher.user)
    db.delete(teacher); db.commit(); return None

@router.post("/students", response_model=StudentOut, status_code=201)
def create_student(payload: StudentCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    data = payload.model_dump(exclude={"email", "password"}); student = Student(**data)
    if payload.email:
        if not payload.password: raise HTTPException(422, "password is required when email is provided")
        email = payload.email.lower()
        if db.scalar(select(User).where(User.email == email)): raise HTTPException(409, "Email already registered")
        student.user = User(email=email, full_name=f"{payload.first_name} {payload.last_name}", role=Role.student, hashed_password=hash_password(payload.password))
    
    db.add(student)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Admission number already exists")
    return student

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

@router.delete("/students/{student_id}", status_code=204)
def delete_student(student_id: int, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    student = db.get(Student, student_id)
    if not student: raise HTTPException(404, "Student not found")
    if student.user: db.delete(student.user)
    db.delete(student); db.commit(); return None

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
    
    existing = db.scalars(select(TimetableEntry).where(
        TimetableEntry.day_of_week == payload.day_of_week, 
        ((TimetableEntry.section_id == payload.section_id) | (TimetableEntry.teacher_id == payload.teacher_id))
    )).all()
    for e in existing:
        if payload.start_time < e.end_time and e.start_time < payload.end_time: 
            raise HTTPException(409, "Timetable conflict: Section or Teacher is already booked at this time")
            
    if payload.room:
        room_conflict = db.scalars(select(TimetableEntry).where(
            TimetableEntry.day_of_week == payload.day_of_week, 
            TimetableEntry.room == payload.room
        )).all()
        for r in room_conflict:
            if payload.start_time < r.end_time and r.start_time < payload.end_time:
                raise HTTPException(409, f"Timetable conflict: Room {payload.room} is already booked at this time")

    entry = TimetableEntry(**payload.model_dump()); db.add(entry); db.commit(); return entry

@router.get("/sections/{section_id}/timetable", response_model=list[TimetableOut])
def section_timetable(section_id: int, db: Session = Depends(get_db), user: User = Depends(staff)):
    assert_section_access(db, user, section_id)
    return db.scalars(select(TimetableEntry).where(TimetableEntry.section_id == section_id).order_by(TimetableEntry.day_of_week, TimetableEntry.start_time)).all()