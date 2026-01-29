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

class BlogBase(BaseSchema):
    """Blog post base schema."""
    title: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=255)
    content: Optional[str] = None
    excerpt: Optional[str] = None
    category_id: Optional[int] = None
    featured_image: Optional[str] = None
    status: str = "draft"
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None
    allow_comments: bool = True
    is_featured: bool = False
    tags: Optional[List[int]] = None

class BlogCreate(BlogBase):
    """Blog post create schema."""
    pass

class BlogUpdate(BaseSchema):
    """Blog post update schema."""
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    category_id: Optional[int] = None
    featured_image: Optional[str] = None
    status: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: Optional[str] = None
    allow_comments: Optional[bool] = None
    is_featured: Optional[bool] = None
    tags: Optional[List[int]] = None

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
