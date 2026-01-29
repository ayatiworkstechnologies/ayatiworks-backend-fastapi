"""
Calendar and Meeting models.
"""

from datetime import datetime, date, time
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, JSON, DateTime, Date, Time
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, AuditMixin


class CalendarEvent(BaseModel, AuditMixin):
    """Calendar event."""
    
    __tablename__ = "calendar_events"
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Time
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    is_all_day = Column(Boolean, default=False)
    timezone = Column(String(50), default="UTC")
    
    # Recurrence
    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(String(255), nullable=True)  # RRULE format
    recurrence_end = Column(Date, nullable=True)
    
    # Location
    location = Column(String(255), nullable=True)
    is_virtual = Column(Boolean, default=False)
    meeting_link = Column(String(500), nullable=True)
    
    # Type
    event_type = Column(String(50), default="event")  # event, meeting, reminder, task
    
    # Organizer
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Color
    color = Column(String(20), default="#3B82F6")
    
    # Visibility
    visibility = Column(String(20), default="private")  # private, public, busy
    
    # Related
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    
    # Relationships
    organizer = relationship("User", backref="organized_events")
    attendees = relationship("EventAttendee", back_populates="event", cascade="all, delete-orphan")


class EventAttendee(BaseModel):
    """Event attendee."""
    
    __tablename__ = "event_attendees"
    
    event_id = Column(Integer, ForeignKey("calendar_events.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # For external attendees
    email = Column(String(255), nullable=True)
    name = Column(String(100), nullable=True)
    
    # Response
    status = Column(String(20), default="pending")  # pending, accepted, declined, tentative
    responded_at = Column(DateTime, nullable=True)
    
    # Role
    role = Column(String(20), default="attendee")  # organizer, attendee, optional
    
    # Relationships
    event = relationship("CalendarEvent", back_populates="attendees")


class Meeting(BaseModel, AuditMixin):
    """Meeting with agenda and minutes."""
    
    __tablename__ = "meetings"
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Time
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60)
    
    # Location
    location = Column(String(255), nullable=True)
    meeting_link = Column(String(500), nullable=True)
    meeting_id = Column(String(100), nullable=True)  # Zoom/Teams ID
    meeting_password = Column(String(50), nullable=True)
    
    # Organizer
    organizer_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    
    # Status
    status = Column(String(20), default="scheduled")  # scheduled, in_progress, completed, cancelled
    
    # Agenda
    agenda = Column(JSON, nullable=True)  # [{topic, duration, presenter}]
    
    # Minutes
    minutes = Column(Text, nullable=True)
    action_items = Column(JSON, nullable=True)  # [{task, assignee, due_date}]
    
    # Related
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    
    # Recording
    recording_url = Column(String(500), nullable=True)
    
    # Relationships
    organizer = relationship("Employee", backref="organized_meetings")


class MeetingParticipant(BaseModel):
    """Meeting participant."""
    
    __tablename__ = "meeting_participants"
    
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    
    # For external participants
    email = Column(String(255), nullable=True)
    name = Column(String(100), nullable=True)
    
    # Attendance
    status = Column(String(20), default="invited")  # invited, accepted, declined, attended
    joined_at = Column(DateTime, nullable=True)
    left_at = Column(DateTime, nullable=True)
    
    # Role
    role = Column(String(20), default="participant")  # organizer, presenter, participant
