from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.blog import Blog, BlogCategory, BlogAuthor, Page, CaseStudy
from app.schemas.blog import (
    BlogCreate, BlogUpdate,
    BlogCategoryCreate, BlogCategoryUpdate,
    BlogAuthorCreate, BlogAuthorUpdate
)

class BlogService:
    def __init__(self, db: Session):
        self.db = db

    # ============== Blog Posts ==============

    def get_all_blogs(
        self,
        category_id: Optional[int] = None,
        author_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Blog], int]:
        query = self.db.query(Blog).filter(Blog.is_deleted == False)

        if category_id:
            query = query.filter(Blog.category_id == category_id)
        if author_id:
            query = query.filter(Blog.author_id == author_id)
        if status:
            query = query.filter(Blog.status == status)
        if search:
            query = query.filter(
                or_(
                    Blog.title.ilike(f"%{search}%"),
                    Blog.content.ilike(f"%{search}%")
                )
            )

        total = query.count()
        blogs = query.order_by(Blog.published_at.desc() if status == "published" else Blog.created_at.desc())\
            .offset((page - 1) * page_size)\
            .limit(page_size)\
            .all()
        return blogs, total

    def get_blog_by_id(self, blog_id: int) -> Optional[Blog]:
        # Use simple get to avoid potential joinedload issues with bad data
        blog = self.db.get(Blog, blog_id)
        if blog and not blog.is_deleted:
            return blog
        return None

    def get_blog_by_slug(self, slug: str, only_published: bool = True) -> Optional[Blog]:
        query = self.db.query(Blog).filter(Blog.slug == slug, Blog.is_deleted == False)
        if only_published:
            query = query.filter(Blog.status == "published")
        return query.first()

    def get_blog_by_slug_and_category(self, slug: str, category_id: int, only_published: bool = True) -> Optional[Blog]:
        """Get blog by slug within a specific category."""
        query = self.db.query(Blog).filter(
            Blog.slug == slug,
            Blog.category_id == category_id,
            Blog.is_deleted == False
        )
        if only_published:
            query = query.filter(Blog.status == "published")
        return query.first()

    def create_blog(self, data: BlogCreate, author_id: int) -> Blog:
        blog = Blog(
            **data.model_dump(exclude={"tags"}),
            author_id=author_id,
            created_by=author_id
        )
        if data.status == "published":
            blog.published_at = datetime.utcnow()
        
        if data.tags:
            blog.tags = data.tags

        self.db.add(blog)
        self.db.commit()
        self.db.refresh(blog)
        return blog

    def update_blog(self, blog_id: int, data: BlogUpdate, updated_by: int) -> Optional[Blog]:
        blog = self.get_blog_by_id(blog_id)
        if not blog:
            return None

        update_data = data.model_dump(exclude_unset=True)
        
        # Handle status change to published
        if "status" in update_data and update_data["status"] == "published" and blog.status != "published":
            blog.published_at = datetime.utcnow()

        for field, value in update_data.items():
            setattr(blog, field, value)

        blog.updated_by = updated_by
        self.db.commit()
        self.db.refresh(blog)
        return blog

    def delete_blog(self, blog_id: int, deleted_by: int) -> bool:
        blog = self.get_blog_by_id(blog_id)
        if not blog:
            return False
        
        blog.is_deleted = True
        blog.deleted_at = datetime.utcnow()
        blog.deleted_by = deleted_by
        self.db.commit()
        return True

    def increment_views(self, blog_id: int):
        self.db.query(Blog).filter(Blog.id == blog_id).update({"views": Blog.views + 1})
        self.db.commit()


class BlogCategoryService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[BlogCategory]:
        return self.db.query(BlogCategory).filter(BlogCategory.is_deleted == False)\
            .order_by(BlogCategory.order).all()

    def get_by_id(self, category_id: int) -> Optional[BlogCategory]:
        return self.db.query(BlogCategory).filter(BlogCategory.id == category_id, BlogCategory.is_deleted == False).first()

    def get_category_by_slug(self, slug: str) -> Optional[BlogCategory]:
        """Get category by slug."""
        return self.db.query(BlogCategory).filter(
            BlogCategory.slug == slug,
            BlogCategory.is_deleted == False
        ).first()

    def create(self, data: BlogCategoryCreate, created_by: int) -> BlogCategory:
        category = BlogCategory(
            **data.model_dump(),
            created_by=created_by
        )
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def update(self, category_id: int, data: BlogCategoryUpdate, updated_by: int) -> Optional[BlogCategory]:
        category = self.get_by_id(category_id)
        if not category:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(category, field, value)

        category.updated_by = updated_by
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete(self, category_id: int, deleted_by: int) -> bool:
        category = self.get_by_id(category_id)
        if not category:
            return False
        
        category.is_deleted = True
        category.deleted_at = datetime.utcnow()
        category.deleted_by = deleted_by
        self.db.commit()
        return True


class BlogAuthorService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[BlogAuthor]:
        return self.db.query(BlogAuthor).filter(BlogAuthor.is_deleted == False).all()

    def get_by_id(self, author_id: int) -> Optional[BlogAuthor]:
        return self.db.query(BlogAuthor).filter(BlogAuthor.id == author_id, BlogAuthor.is_deleted == False).first()

    def get_by_user_id(self, user_id: int) -> Optional[BlogAuthor]:
        return self.db.query(BlogAuthor).filter(BlogAuthor.user_id == user_id, BlogAuthor.is_deleted == False).first()

    def create(self, data: BlogAuthorCreate, created_by: int) -> BlogAuthor:
        author = BlogAuthor(
            **data.model_dump(),
            created_by=created_by
        )
        self.db.add(author)
        self.db.commit()
        self.db.refresh(author)
        return author

    def update(self, author_id: int, data: BlogAuthorUpdate, updated_by: int) -> Optional[BlogAuthor]:
        author = self.get_by_id(author_id)
        if not author:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(author, field, value)

        author.updated_by = updated_by
        self.db.commit()
        self.db.refresh(author)
        return author

    def delete(self, author_id: int, deleted_by: int) -> bool:
        author = self.get_by_id(author_id)
        if not author:
            return False
        
        author.is_deleted = True
        author.deleted_at = datetime.utcnow()
        author.deleted_by = deleted_by
        self.db.commit()
        return True
