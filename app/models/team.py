"""
Team models.
Cross-functional team management.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import date

from app.models.base import BaseModel, AuditMixin


class Team(BaseModel, AuditMixin):
    """
    Team model for managing cross-functional teams.
    Teams can span across departments and have specific purposes.
    """
    
    __tablename__ = "teams"
    
    # Basic Information
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    team_type = Column(String(50), nullable=True)  # web, social_media, content, video, design, hr, etc.
    
    # Organization
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)  # Optional parent department
    
    # Leadership
    team_lead_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Settings
    max_members = Column(Integer, nullable=True)  # Optional team size limit
    
    # Relationships
    company = relationship("Company", back_populates="teams")
    department = relationship("Department")
    team_lead = relationship("User", foreign_keys=[team_lead_id])
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")


class TeamMember(BaseModel, AuditMixin):
    """
    Team membership model (many-to-many relationship).
    Tracks which employees belong to which teams.
    """
    
    __tablename__ = "team_members"
    
    # Core relationship
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    
    # Member details
    role = Column(String(50), nullable=True)  # Role within team: "Lead", "Senior", "Junior", etc.
    joined_date = Column(Date, nullable=False, default=date.today)
    
    # Relationships
    team = relationship("Team", back_populates="members")
    employee = relationship("Employee")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('team_id', 'employee_id', name='uq_team_employee'),
    )
