from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import BaseSchema, TimestampSchema

# ============== Blog Category Schemas ==============

class BlogCategoryBase(BaseSchema):
    """Blog category base schema."""
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    order: int = 0
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None

class BlogCategoryCreate(BlogCategoryBase):
    """Blog category create schema."""
    pass

class BlogCategoryUpdate(BaseSchema):
    """Blog category update schema."""
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    order: Optional[int] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None

class BlogCategoryResponse(BlogCategoryBase, TimestampSchema):
    """Blog category response schema."""
    id: int


# ============== Blog Author Schemas ==============

class BlogAuthorBase(BaseSchema):
    """Blog author base schema."""
    display_name: Optional[str] = None
    bio: Optional[str] = None
    social_links: Optional[dict] = None

class BlogAuthorCreate(BlogAuthorBase):
    """Blog author create schema."""
    user_id: int

class BlogAuthorUpdate(BlogAuthorBase):
    """Blog author update schema."""
    pass

class BlogAuthorResponse(BlogAuthorBase, TimestampSchema):
    """Blog author response schema."""
    id: int
    user_id: int


# ============== Blog Post Schemas ==============

# Section schema for dynamic content blocks
class BlogSection(BaseSchema):
    """Blog section schema for dynamic content blocks."""
    # Section type: content, image, quote, code, video, cta
    section_type: Optional[str] = "content"
    
    # Common fields
    heading: Optional[str] = None
    heading_level: Optional[str] = "h2"  # h2, h3, h4
    
    # Content section
    content: Optional[str] = None  # HTML content from rich text editor
    
    # Image section
    image: Optional[str] = None  # Image URL
    image_alt: Optional[str] = None  # Image alt text
    image_caption: Optional[str] = None  # Image caption
    
    # Quote section
    quote: Optional[str] = None
    quote_author: Optional[str] = None
    
    # Code section
    code: Optional[str] = None
    code_language: Optional[str] = "javascript"
    
    # Video section
    video_url: Optional[str] = None
    
    # CTA section
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    cta_style: Optional[str] = "primary"  # primary, secondary, gradient

class BlogBase(BaseSchema):
    """Blog post base schema."""
    title: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=255)
    
    # Banner
    banner_image: Optional[str] = None
    banner_image_alt: Optional[str] = None
    banner_title: Optional[str] = None
    
    # Content
    content: Optional[str] = None
    excerpt: Optional[str] = None
    
    # Dynamic sections (array of section objects)
    sections: Optional[List[dict]] = None  # List of BlogSection dicts
    
    # Category
    category_id: Optional[int] = None
    featured_image: Optional[str] = None
    featured_image_alt: Optional[str] = None
    
    # Blog date and read time
    blog_date: Optional[datetime] = None
    read_time: Optional[int] = None  # in minutes
    
    # Status and SEO
    status: str = "draft"
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None
    allow_comments: bool = True
    is_featured: bool = False
    tags: Optional[List[str]] = None

class BlogCreate(BlogBase):
    """Blog post create schema."""
    author_id: Optional[int] = None

class BlogUpdate(BaseSchema):
    """Blog post update schema."""
    title: Optional[str] = None
    slug: Optional[str] = None
    
    # Banner
    banner_image: Optional[str] = None
    banner_image_alt: Optional[str] = None
    banner_title: Optional[str] = None
    
    # Content
    content: Optional[str] = None
    excerpt: Optional[str] = None
    sections: Optional[List[dict]] = None
    
    # Category
    category_id: Optional[int] = None
    featured_image: Optional[str] = None
    featured_image_alt: Optional[str] = None
    
    # Blog date and read time
    blog_date: Optional[datetime] = None
    read_time: Optional[int] = None
    
    # Status and SEO
    status: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None
    allow_comments: Optional[bool] = None
    is_featured: Optional[bool] = None
    tags: Optional[List[str]] = None
    author_id: Optional[int] = None

class BlogResponse(BlogBase, TimestampSchema):
    """Blog post response schema."""
    id: int
    author_id: int
    published_at: Optional[datetime] = None
    views: int = 0
    likes: int = 0
    
    # Nested display data
    author_name: Optional[str] = None
    category_name: Optional[str] = None
    category_slug: Optional[str] = None  # For URL generation
    
    # Full nested objects
    author_profile: Optional[BlogAuthorResponse] = None
    category: Optional[BlogCategoryResponse] = None


