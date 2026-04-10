from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Boolean,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from app.db.session import Base


# ==========================================
# ORGANIZATION (TENANT)
# ==========================================
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    plan = Column(String, default="basic", nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("User", back_populates="organization")
    reports = relationship("Report", back_populates="organization")
    subscription = relationship(
        "Subscription",
        back_populates="organization",
        uselist=False
    )


# ==========================================
# USER
# ==========================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String, nullable=True)
    mobile_number = Column(String, unique=True, index=True, nullable=True)
    password = Column(String, nullable=False)
    kyc_verified = Column(Boolean, default=False, nullable=False)

    tenant_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    # 🔥 Multi-role system
    # super_admin | admin | manager | user
    role = Column(String, default="user", nullable=False)

    # 🔥 Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)
    abuse_warnings = Column(Integer, default=0, nullable=False)
    signup_source = Column(String, nullable=True)
    signup_ip = Column(String, nullable=True)
    signup_user_agent = Column(String, nullable=True)
    signup_referrer = Column(String, nullable=True)
    signup_accept_language = Column(String, nullable=True)
    signup_locale = Column(String, nullable=True)
    signup_timezone = Column(String, nullable=True)
    signup_city = Column(String, nullable=True)
    signup_country = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="users")
    reports = relationship("Report", back_populates="user")

    @property
    def is_admin(self) -> bool:
        return self.role in ["admin", "super_admin"]


# ==========================================
# SUBSCRIPTION (ORG LEVEL)
# ==========================================
class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    plan_name = Column(String, default="basic", nullable=False)
    is_active = Column(Boolean, default=False)

    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)

    reports_used = Column(Integer, default=0)
    last_reset_date = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="subscription")


# ==========================================
# REPORT
# ==========================================
class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)

    content = Column(JSONB, nullable=False)
    engine_version = Column(String, default="v1")
    confidence_score = Column(Integer, default=75)

    tenant_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    is_deleted = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    organization = relationship("Organization", back_populates="reports")
    user = relationship("User", back_populates="reports")


# ==========================================
# PAYMENT
# ==========================================
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    tenant_id = Column(Integer)

    plan_name = Column(String)

    razorpay_order_id = Column(String, unique=True)
    razorpay_payment_id = Column(String)
    razorpay_signature = Column(String)

    amount = Column(Integer)
    currency = Column(String, default="INR")
    status = Column(String, default="created")

    created_at = Column(DateTime, default=datetime.utcnow)


# ==========================================
# AUDIT LOG
# ==========================================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, nullable=False, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)

    action = Column(String, nullable=False)
    details = Column(JSONB)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


# ==========================================
# SUPER ADMIN KNOWLEDGE ASSETS
# ==========================================
class KnowledgeAsset(Base):
    __tablename__ = "knowledge_assets"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=True, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    domain = Column(String, nullable=True, default="numerology")  # numerology | swar_vigyan
    source_type = Column(String, nullable=False)  # pdf | audio | text
    language = Column(String, nullable=True)      # hindi | english | bilingual
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)

    file_name = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    content_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)

    status = Column(String, default="uploaded", nullable=False)  # uploaded | processing | review | applied | failed

    approval_status = Column(String, default="pending", nullable=False)  # pending | approved | rejected
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_notes = Column(Text, nullable=True)
    manual_notes = Column(JSONB, nullable=True)

    extracted_text = Column(Text, nullable=True)
    transcript_text = Column(Text, nullable=True)
    deterministic_updates = Column(JSONB, nullable=True)
    prompt_notes = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    user = relationship("User", foreign_keys=[uploaded_by])
    approver = relationship("User", foreign_keys=[approved_by])




