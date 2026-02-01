from datetime import datetime

from pydantic import Field

from app.schemas.common import BaseSchema, TimestampSchema

# ============== Blog Category Schemas ==============

class BlogCategoryBase(BaseSchema):
    """Blog category base schema."""
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=100)
    description: str | None = None
    parent_id: int | None = None
    order: int = 0
    meta_title: str | None = None
    meta_description: str | None = None

class BlogCategoryCreate(BlogCategoryBase):
    """Blog category create schema."""
    pass

class BlogCategoryUpdate(BaseSchema):
    """Blog category update schema."""
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    parent_id: int | None = None
    order: int | None = None
    meta_title: str | None = None
    meta_description: str | None = None

class BlogCategoryResponse(BlogCategoryBase, TimestampSchema):
    """Blog category response schema."""
    id: int


# ============== Blog Author Schemas ==============

class BlogAuthorBase(BaseSchema):
    """Blog author base schema."""
    display_name: str | None = None
    bio: str | None = None
    social_links: dict | None = None

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
    section_type: str | None = "content"

    # Common fields
    heading: str | None = None
    heading_level: str | None = "h2"  # h2, h3, h4

    # Content section
    content: str | None = None  # HTML content from rich text editor

    # Image section
    image: str | None = None  # Image URL
    image_alt: str | None = None  # Image alt text
    image_caption: str | None = None  # Image caption

    # Quote section
    quote: str | None = None
    quote_author: str | None = None

    # Code section
    code: str | None = None
    code_language: str | None = "javascript"

    # Video section
    video_url: str | None = None

    # CTA section
    cta_text: str | None = None
    cta_url: str | None = None
    cta_style: str | None = "primary"  # primary, secondary, gradient

class BlogBase(BaseSchema):
    """Blog post base schema."""
    title: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=255)

    # Banner
    banner_image: str | None = None
    banner_image_alt: str | None = None
    banner_title: str | None = None

    # Content
    content: str | None = None
    excerpt: str | None = None

    # Dynamic sections (array of section objects)
    sections: list[dict] | None = None  # List of BlogSection dicts

    # FAQs
    faqs: list[dict] | None = None  # List of {question, answer} dicts

    # Category
    category_id: int | None = None
    featured_image: str | None = None
    featured_image_alt: str | None = None

    # Blog date and read time
    blog_date: datetime | None = None
    read_time: int | None = None  # in minutes

    # Status and SEO
    status: str = "draft"
    meta_title: str | None = None
    meta_description: str | None = None
    meta_keywords: str | None = None
    allow_comments: bool = True
    is_featured: bool = False
    tags: list[str] | None = None

class BlogCreate(BlogBase):
    """Blog post create schema."""
    author_id: int | None = None

class BlogUpdate(BaseSchema):
    """Blog post update schema."""
    title: str | None = None
    slug: str | None = None

    # Banner
    banner_image: str | None = None
    banner_image_alt: str | None = None
    banner_title: str | None = None

    # Content
    content: str | None = None
    excerpt: str | None = None
    sections: list[dict] | None = None
    faqs: list[dict] | None = None

    # Category
    category_id: int | None = None
    featured_image: str | None = None
    featured_image_alt: str | None = None

    # Blog date and read time
    blog_date: datetime | None = None
    read_time: int | None = None

    # Status and SEO
    status: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    meta_keywords: str | None = None
    allow_comments: bool | None = None
    is_featured: bool | None = None
    tags: list[str] | None = None
    author_id: int | None = None

class BlogResponse(BlogBase, TimestampSchema):
    """Blog post response schema."""
    id: int
    author_id: int
    published_at: datetime | None = None
    views: int = 0
    likes: int = 0

    # Nested display data
    author_name: str | None = None
    category_name: str | None = None
    category_slug: str | None = None  # For URL generation

    # Full nested objects
    author_profile: BlogAuthorResponse | None = None
    category: BlogCategoryResponse | None = None



