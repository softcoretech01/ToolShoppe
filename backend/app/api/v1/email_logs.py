from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.email_log import EmailLog
from app.schemas.email_log import EmailLogOut
from app.schemas.response import SuccessResponse

router = APIRouter(prefix="/email-logs", tags=["5. Email Communications"])
api_alias_router = APIRouter(prefix="/api/email-logs", tags=["5. Email Communications"])


@router.get(
    "",
    response_model=SuccessResponse[List[EmailLogOut]],
    summary="List Sent Email Logs",
    description="Retrieve all outbound email records dispatched by the system (RFQs, quotations, etc.)."
)
@api_alias_router.get(
    "",
    response_model=SuccessResponse[List[EmailLogOut]],
    summary="List Sent Email Logs",
)
def list_email_logs(
    document_type: Optional[str] = Query(None, description="Filter by document type (e.g. 'RFQ')"),
    document_id: Optional[int] = Query(None, description="Filter by linked document ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(EmailLog)
    if document_type:
        query = query.filter(EmailLog.document_type == document_type)
    if document_id:
        query = query.filter(EmailLog.document_id == document_id)

    logs = query.order_by(EmailLog.sent_at.desc()).offset(skip).limit(limit).all()
    return SuccessResponse(
        success=True,
        message="Email logs retrieved successfully.",
        data=[EmailLogOut.model_validate(log) for log in logs],
    )


@router.get(
    "/inbox",
    summary="Fetch Recent Incoming Emails / Supplier Replies via IMAP",
)
@api_alias_router.get(
    "/inbox",
    summary="Fetch Recent Incoming Emails / Supplier Replies via IMAP",
)
def get_inbox_emails(
    limit: int = Query(15, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    from app.core.email import fetch_inbox_messages

    messages = fetch_inbox_messages(limit=limit)
    return SuccessResponse(
        success=True,
        message=f"Fetched {len(messages)} recent messages from inbox.",
        data=messages,
    )


@router.get(
    "/{id}",
    response_model=SuccessResponse[EmailLogOut],
    summary="Get Single Email Log by ID",
    description="Retrieve full details for a single email log entry."
)
@api_alias_router.get(
    "/{id}",
    response_model=SuccessResponse[EmailLogOut],
    summary="Get Single Email Log by ID",
)
def get_email_log(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    log = db.query(EmailLog).filter(EmailLog.id == id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email log {id} not found."
        )
    return SuccessResponse(
        success=True,
        message="Email log retrieved successfully.",
        data=EmailLogOut.model_validate(log),
    )


class SendEmailDirectRequest(BaseModel):
    recipient: str
    subject: str
    body: str
    document_type: Optional[str] = "General"
    document_id: Optional[int] = 0


@router.post(
    "/send-live",
    response_model=SuccessResponse[EmailLogOut],
    summary="Send Real Email via Gmail SMTP",
)
@api_alias_router.post(
    "/send-live",
    response_model=SuccessResponse[EmailLogOut],
    summary="Send Real Email via Gmail SMTP",
)
def send_live_email_endpoint(
    req: SendEmailDirectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.core.email import send_live_email

    delivery_res = send_live_email(recipients=req.recipient, subject=req.subject, body=req.body)
    log = EmailLog(
        document_type=req.document_type or "General",
        document_id=req.document_id or 0,
        recipient=req.recipient,
        subject=req.subject,
        body=req.body,
        status=delivery_res.status,
        error_message=delivery_res.error_message,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    msg = "Real email dispatched successfully."
    if delivery_res.status == "Simulated":
        msg = "Email recorded in simulation mode (SMTP not enabled or credentials missing)."
    elif delivery_res.status == "Failed":
        msg = f"Failed to send email: {delivery_res.error_message}"

    return SuccessResponse(
        success=delivery_res.success,
        message=msg,
        data=EmailLogOut.model_validate(log),
    )


