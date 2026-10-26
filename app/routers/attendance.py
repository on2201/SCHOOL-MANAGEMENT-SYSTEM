from datetime import date as date_type
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
