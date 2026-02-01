"""
Public facing models for Contact and Careers.
"""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.models.base import BaseModel


class ContactEnquiry(BaseModel):
    """
    Contact Us form submissions.
    """
    __tablename__ = "contact_enquiries"

    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    subject = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    # Status tracking
    status = Column(String(20), default="new")  # new, read, replied
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ContactEnquiry {self.name} - {self.subject}>"


class CareerApplication(BaseModel):
    """
    Job applications from Careers page.
    """
    __tablename__ = "career_applications"

    # Candidate Info
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)

    # Job Info
    position_applied = Column(String(100), nullable=False)
    experience_years = Column(Integer, nullable=True)
    current_company = Column(String(100), nullable=True)

    # Links & Files
    portfolio_url = Column(String(255), nullable=True)
    linkedin_url = Column(String(255), nullable=True)
    resume_url = Column(String(255), nullable=True)  # URL to uploaded file
    cover_letter = Column(Text, nullable=True)

    # Status
    status = Column(String(20), default="new")  # new, reviewed, interviewed, rejected, hired
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CareerApplication {self.first_name} {self.last_name} - {self.position_applied}>"

