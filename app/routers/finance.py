from decimal import Decimal
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
