from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db, engine
from app.models.blog import Blog
from app.models.auth import User

def debug_blog():
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        print("--- Debugging Blog ID 1 ---")
        # Raw SQL check
        result = db.execute(text("SELECT id, title, slug, is_deleted, author_id FROM blogs WHERE id = 1"))
        row = result.fetchone()
        if row:
            print(f"Raw SQL found: {row}")
        else:
            print("Raw SQL: Blog ID 1 NOT FOUND")

        # SQLAlchemy Query check
        blog = db.query(Blog).filter(Blog.id == 1).first()
        if blog:
             print(f"SQLAlchemy Query found: ID={blog.id}, Title={blog.title}, Deleted={blog.is_deleted}")
             # Check relationships
             print(f"Author: {blog.author}")
             if blog.author:
                 print(f"Author Name: {blog.author.full_name}")
        else:
             print("SQLAlchemy Query: Blog ID 1 NOT FOUND")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_blog()
