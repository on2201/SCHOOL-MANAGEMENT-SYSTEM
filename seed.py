"""Idempotent dev seed. Run: python seed.py"""
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
