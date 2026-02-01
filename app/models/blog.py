"""
Blog and CMS models.
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import AuditMixin, BaseModel


class BlogCategory(BaseModel, AuditMixin):
    """Blog category."""

    __tablename__ = "blog_categories"

    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    parent_id = Column(Integer, ForeignKey("blog_categories.id"), nullable=True)

    # SEO
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)

    order = Column(Integer, default=0)


class BlogAuthor(BaseModel, AuditMixin):
    """Blog author profile."""

    __tablename__ = "blog_authors"

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    display_name = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    social_links = Column(JSON, nullable=True)  # {"twitter": "...", "linkedin": "..."}

    # Relationships
    user = relationship("User", backref="blog_author_profile")


class BlogTag(BaseModel):
    """Blog tag."""

    __tablename__ = "blog_tags"

    name = Column(String(50), nullable=False)
    slug = Column(String(50), unique=True, nullable=False, index=True)


class Blog(BaseModel, AuditMixin):
    """Blog post."""

    __tablename__ = "blogs"

    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)

    # Banner
    banner_image = Column(String(500), nullable=True)
    banner_image_alt = Column(String(255), nullable=True)
    banner_title = Column(String(255), nullable=True)

    # Content
    excerpt = Column(Text, nullable=True)
    content = Column(Text, nullable=True)

    # Dynamic Sections (JSON array)
    # Each section: {"heading": "...", "content": "...(HTML)", "image": "...(optional URL)"}
    sections = Column(JSON, nullable=True)
    
    # FAQs (JSON array)
    # [{"question": "...", "answer": "..."}]
    faqs = Column(JSON, nullable=True)

    # Author
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Category
    category_id = Column(Integer, ForeignKey("blog_categories.id"), nullable=True)

    # Featured image (keep for backward compatibility)
    featured_image = Column(String(500), nullable=True)
    featured_image_alt = Column(String(255), nullable=True)

    # Blog date and read time
    blog_date = Column(DateTime, nullable=True, default=datetime.utcnow)
    read_time = Column(Integer, nullable=True)  # in minutes

    # Status
    status = Column(String(20), default="draft")  # draft, published, archived
    published_at = Column(DateTime, nullable=True)

    # SEO
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)
    meta_keywords = Column(String(500), nullable=True)

    # Engagement
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)

    # Settings
    allow_comments = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)

    # Tags (JSON array of tag IDs)
    tags = Column(JSON, nullable=True)

    # Relationships
    author = relationship("User", backref="blogs")
    category = relationship("BlogCategory", backref="blogs")
    comments = relationship("BlogComment", back_populates="blog", cascade="all, delete-orphan")


class BlogComment(BaseModel, AuditMixin):
    """Blog comment."""

    __tablename__ = "blog_comments"

    blog_id = Column(Integer, ForeignKey("blogs.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # For guest comments
    author_name = Column(String(100), nullable=True)
    author_email = Column(String(255), nullable=True)

    content = Column(Text, nullable=False)

    # Reply to
    parent_id = Column(Integer, ForeignKey("blog_comments.id"), nullable=True)

    # Status
    status = Column(String(20), default="pending")  # pending, approved, spam

    # Relationships
    blog = relationship("Blog", back_populates="comments")


class Page(BaseModel, AuditMixin):
    """Static page (About, Contact, etc.)."""

    __tablename__ = "pages"

    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)

    content = Column(Text, nullable=True)

    # Template
    template = Column(String(50), default="default")

    # Status
    status = Column(String(20), default="draft")
    published_at = Column(DateTime, nullable=True)

    # SEO
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)

    # Page settings
    show_in_menu = Column(Boolean, default=False)
    menu_order = Column(Integer, default=0)

    parent_id = Column(Integer, ForeignKey("pages.id"), nullable=True)


class CaseStudy(BaseModel, AuditMixin):
    """Case study / Portfolio item."""

    __tablename__ = "case_studies"

    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)

    # Client
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    client_name = Column(String(255), nullable=True)  # If no client record

    # Content
    summary = Column(Text, nullable=True)
    challenge = Column(Text, nullable=True)
    solution = Column(Text, nullable=True)
    results = Column(Text, nullable=True)

    # Media
    featured_image = Column(String(500), nullable=True)
    featured_image_alt = Column(String(255), nullable=True)
    gallery = Column(JSON, nullable=True)  # Array of image URLs

    # Metrics
    metrics = Column(JSON, nullable=True)  # {roi: "20%", time_saved: "50 hours", etc}

    # Project info
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    industry = Column(String(100), nullable=True)
    services = Column(JSON, nullable=True)  # Array of services provided

    # Testimonial
    testimonial = Column(Text, nullable=True)
    testimonial_author = Column(String(100), nullable=True)
    testimonial_role = Column(String(100), nullable=True)

    # Status
    status = Column(String(20), default="draft")
    published_at = Column(DateTime, nullable=True)
    is_featured = Column(Boolean, default=False)

    # SEO
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(Text, nullable=True)

