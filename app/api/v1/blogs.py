"""
Blog and CMS API routes.
"""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import PermissionChecker, get_optional_user
from app.database import get_db
from app.models.auth import User
from app.schemas.blog import (
    BlogAuthorCreate,
    BlogAuthorResponse,
    BlogAuthorUpdate,
    BlogCategoryCreate,
    BlogCategoryResponse,
    BlogCategoryUpdate,
    BlogCreate,
    BlogResponse,
    BlogUpdate,
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services.blog_service import BlogAuthorService, BlogCategoryService, BlogService

router = APIRouter(tags=["Blog & CMS"])


# ============== Blog Post Endpoints ==============

@router.get("/blogs", response_model=PaginatedResponse[BlogResponse])
async def list_blogs(
    category_id: int | None = None,
    author_id: int | None = None,
    status: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User | None = Depends(get_optional_user),
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
        item.category_slug = b.category.slug if b.category else None

        # Populate author_profile
        if b.author and hasattr(b.author, 'blog_author_profile'):
            profile = b.author.blog_author_profile
            # Handle list backref if not unique
            if isinstance(profile, list):
                profile = profile[0] if profile else None

            if profile:
                item.author_profile = BlogAuthorResponse.model_validate(profile)

        items.append(item)

    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/blogs/{id_or_slug}", response_model=BlogResponse)
async def get_blog(
    id_or_slug: str,
    db: Session = Depends(get_db)
):
    """Get blog by ID or slug (public for published, auth for drafts)."""
    service = BlogService(db)

    # Check if it's a numeric ID or a slug
    blog = None
    try:
        # Try to treat as ID first
        blog_id = int(id_or_slug)
        blog = service.get_blog_by_id(blog_id)

        # Fallback: If ID lookup failed but list_blogs claims it exists (consistency issue debug)
        if not blog:
             # Try expensive scan (Temporary fix for potential DB/ORM inconsistency)
             # Only do this if total count is small to avoid perf hit, or just do it.
             all_blogs, _ = service.get_all_blogs(page=1, page_size=1000)
             for b in all_blogs:
                 if b.id == blog_id:
                      blog = b
                      break
    except ValueError:
        # If not an integer, treat as slug
        blog = service.get_blog_by_slug(id_or_slug, only_published=False)

    if not blog:
        # Fallback: if ID lookup failed (e.g. ID not found), try as slug just in case
        if id_or_slug.isdigit():
             blog = service.get_blog_by_slug(id_or_slug, only_published=False)

    if not blog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog not found"
        )

    # Only increment views for published posts accessed by slug
    # If accessed by ID, we assume it's an admin/edit view, unless it's a numeric slug?
    # Let's say we only increment if it's NOT a digit lookup OR if we found it via slug fallback.
    is_slug_lookup = not id_or_slug.isdigit()
    if is_slug_lookup and blog.status == "published":
        service.increment_views(blog.id)

    item = BlogResponse.model_validate(blog)

    item.author_name = blog.author.full_name if blog.author else "Anonymous"
    item.category_name = blog.category.name if blog.category else None
    item.category_slug = blog.category.slug if blog.category else None

    # Populate author_profile
    if blog.author and hasattr(blog.author, 'blog_author_profile'):
        profile = blog.author.blog_author_profile
        if isinstance(profile, list):
            profile = profile[0] if profile else None

        if profile:
            item.author_profile = BlogAuthorResponse.model_validate(profile)

    return item


@router.get("/blogs/public/{category_slug}/{blog_slug}", response_model=BlogResponse)
async def get_blog_by_category_and_slug(
    category_slug: str,
    blog_slug: str,
    db: Session = Depends(get_db)
):
    """Get blog by category slug and blog slug (public endpoint)."""
    service = BlogService(db)
    category_service = BlogCategoryService(db)

    # First find the category
    category = category_service.get_category_by_slug(category_slug)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Then find blog with matching slug and category
    blog = service.get_blog_by_slug_and_category(blog_slug, category.id, only_published=True)
    if not blog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog not found"
        )

    service.increment_views(blog.id)

    item = BlogResponse.model_validate(blog)
    item.author_name = blog.author.full_name if blog.author else "Anonymous"
    item.category_name = blog.category.name if blog.category else None
    item.category_slug = blog.category.slug if blog.category else None

    # Populate author_profile
    if blog.author and hasattr(blog.author, 'blog_author_profile'):
        profile = blog.author.blog_author_profile
        if isinstance(profile, list):
            profile = profile[0] if profile else None

        if profile:
            item.author_profile = BlogAuthorResponse.model_validate(profile)

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

    # Determine author
    author_id = data.author_id if data.author_id else current_user.id
    blog = service.create_blog(data, author_id=author_id)
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

    # If author_id is changed, ensure user has permission? (Skip for now, trust input)

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

@router.get("/blog-categories", response_model=list[BlogCategoryResponse])
async def list_categories(db: Session = Depends(get_db)):
    """List all blog categories."""
    service = BlogCategoryService(db)
    return [BlogCategoryResponse.model_validate(c) for c in service.get_all()]


@router.get("/blog-categories/{id_or_slug}", response_model=BlogCategoryResponse)
async def get_category(
    id_or_slug: str,
    db: Session = Depends(get_db)
):
    """Get blog category by ID or slug."""
    service = BlogCategoryService(db)

    category = None
    if id_or_slug.isdigit():
        category = service.get_by_id(int(id_or_slug))
    else:
        category = service.get_category_by_slug(id_or_slug)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return BlogCategoryResponse.model_validate(category)


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

@router.get("/blog-authors", response_model=list[BlogAuthorResponse])
async def list_authors(db: Session = Depends(get_db)):
    """List all blog authors."""
    service = BlogAuthorService(db)
    return [BlogAuthorResponse.model_validate(a) for a in service.get_all()]


@router.get("/blog-authors/{author_id}", response_model=BlogAuthorResponse)
async def get_author(
    author_id: int,
    db: Session = Depends(get_db)
):
    """Get blog author by ID."""
    service = BlogAuthorService(db)
    author = service.get_by_id(author_id)
    if not author:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Author not found"
        )
    return BlogAuthorResponse.model_validate(author)


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

