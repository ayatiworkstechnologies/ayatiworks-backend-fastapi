"""
Blog and CMS API routes.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_active_user, get_optional_user, PermissionChecker
from app.models.auth import User
from app.schemas.common import PaginatedResponse, MessageResponse
from app.schemas.blog import (
    BlogCreate, BlogUpdate, BlogResponse,
    BlogCategoryCreate, BlogCategoryUpdate, BlogCategoryResponse,
    BlogAuthorCreate, BlogAuthorUpdate, BlogAuthorResponse
)
from app.services.blog_service import BlogService, BlogCategoryService, BlogAuthorService

router = APIRouter(tags=["Blog & CMS"])


# ============== Blog Post Endpoints ==============

@router.get("/blogs", response_model=PaginatedResponse[BlogResponse])
async def list_blogs(
    category_id: Optional[int] = None,
    author_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """List all published blogs (public) or all blogs (authenticated)."""
    service = BlogService(db)
    
    # Public users only see published
    if not current_user:
        status = "published"
    
    blogs, total = service.get_all_blogs(
        category_id=category_id,
        author_id=author_id,
        status=status,
        search=search,
        page=page,
        page_size=page_size
    )
    
    # Convert to response objects with display names
    items = []
    for b in blogs:
        item = BlogResponse.model_validate(b)
        item.author_name = b.author.full_name if b.author else "Anonymous"
        item.category_name = b.category.name if b.category else None
        items.append(item)
        
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/blogs/{slug}", response_model=BlogResponse)
async def get_blog(
    slug: str,
    db: Session = Depends(get_db)
):
    """Get blog by slug (public)."""
    service = BlogService(db)
    blog = service.get_blog_by_slug(slug, only_published=True)
    
    if not blog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog not found"
        )
    
    service.increment_views(blog.id)
    
    item = BlogResponse.model_validate(blog)
    item.author_name = blog.author.full_name if blog.author else "Anonymous"
    item.category_name = blog.category.name if blog.category else None
    return item


@router.post("/blogs", response_model=BlogResponse, status_code=status.HTTP_201_CREATED)
async def create_blog(
    data: BlogCreate,
    current_user: User = Depends(PermissionChecker("blog.create")),
    db: Session = Depends(get_db)
):
    """Create a new blog post."""
    service = BlogService(db)
    
    # Check slug uniqueness
    if service.get_blog_by_slug(data.slug, only_published=False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slug already exists"
        )
    
    blog = service.create_blog(data, author_id=current_user.id)
    return BlogResponse.model_validate(blog)


@router.put("/blogs/{blog_id}", response_model=BlogResponse)
async def update_blog(
    blog_id: int,
    data: BlogUpdate,
    current_user: User = Depends(PermissionChecker("blog.edit")),
    db: Session = Depends(get_db)
):
    """Update a blog post."""
    service = BlogService(db)
    blog = service.update_blog(blog_id, data, updated_by=current_user.id)
    
    if not blog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog not found"
        )
    
    return BlogResponse.model_validate(blog)


@router.delete("/blogs/{blog_id}", response_model=MessageResponse)
async def delete_blog(
    blog_id: int,
    current_user: User = Depends(PermissionChecker("blog.delete")),
    db: Session = Depends(get_db)
):
    """Delete a blog post."""
    service = BlogService(db)
    if not service.delete_blog(blog_id, deleted_by=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog not found"
        )
    return MessageResponse(message="Blog deleted successfully")


# ============== Blog Category Endpoints ==============

@router.get("/blog-categories", response_model=List[BlogCategoryResponse])
async def list_categories(db: Session = Depends(get_db)):
    """List all blog categories."""
    service = BlogCategoryService(db)
    return [BlogCategoryResponse.model_validate(c) for c in service.get_all()]


@router.post("/blog-categories", response_model=BlogCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: BlogCategoryCreate,
    current_user: User = Depends(PermissionChecker("blog.create")),
    db: Session = Depends(get_db)
):
    """Create a new blog category."""
    service = BlogCategoryService(db)
    category = service.create(data, created_by=current_user.id)
    return BlogCategoryResponse.model_validate(category)


@router.put("/blog-categories/{category_id}", response_model=BlogCategoryResponse)
async def update_category(
    category_id: int,
    data: BlogCategoryUpdate,
    current_user: User = Depends(PermissionChecker("blog.edit")),
    db: Session = Depends(get_db)
):
    """Update a blog category."""
    service = BlogCategoryService(db)
    category = service.update(category_id, data, updated_by=current_user.id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return BlogCategoryResponse.model_validate(category)


@router.delete("/blog-categories/{category_id}", response_model=MessageResponse)
async def delete_category(
    category_id: int,
    current_user: User = Depends(PermissionChecker("blog.delete")),
    db: Session = Depends(get_db)
):
    """Delete a blog category."""
    service = BlogCategoryService(db)
    if not service.delete(category_id, deleted_by=current_user.id):
        raise HTTPException(status_code=404, detail="Category not found")
    return MessageResponse(message="Category deleted successfully")


# ============== Blog Author Endpoints ==============

@router.get("/blog-authors", response_model=List[BlogAuthorResponse])
async def list_authors(db: Session = Depends(get_db)):
    """List all blog authors."""
    service = BlogAuthorService(db)
    return [BlogAuthorResponse.model_validate(a) for a in service.get_all()]


@router.post("/blog-authors", response_model=BlogAuthorResponse, status_code=status.HTTP_201_CREATED)
async def create_author(
    data: BlogAuthorCreate,
    current_user: User = Depends(PermissionChecker("blog.create")),
    db: Session = Depends(get_db)
):
    """Create a new blog author profile."""
    service = BlogAuthorService(db)
    # Check if profile already exists for user
    if service.get_by_user_id(data.user_id):
        raise HTTPException(status_code=400, detail="Author profile already exists for this user")
    
    author = service.create(data, created_by=current_user.id)
    return BlogAuthorResponse.model_validate(author)


@router.put("/blog-authors/{author_id}", response_model=BlogAuthorResponse)
async def update_author(
    author_id: int,
    data: BlogAuthorUpdate,
    current_user: User = Depends(PermissionChecker("blog.edit")),
    db: Session = Depends(get_db)
):
    """Update a blog author profile."""
    service = BlogAuthorService(db)
    author = service.update(author_id, data, updated_by=current_user.id)
    if not author:
        raise HTTPException(status_code=404, detail="Author profile not found")
    return BlogAuthorResponse.model_validate(author)


@router.delete("/blog-authors/{author_id}", response_model=MessageResponse)
async def delete_author(
    author_id: int,
    current_user: User = Depends(PermissionChecker("blog.delete")),
    db: Session = Depends(get_db)
):
    """Delete a blog author profile."""
    service = BlogAuthorService(db)
    if not service.delete(author_id, deleted_by=current_user.id):
        raise HTTPException(status_code=404, detail="Author profile not found")
    return MessageResponse(message="Author profile deleted successfully")
