from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import engine
from app.models.blog import Blog
import traceback

def debug_trace():
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        print("Tracing ORM Query for ID 1...")
        blog = db.query(Blog).filter(Blog.id == 1).first()
        if blog:
             print(f"Success! Found blog: {blog.title}")
        else:
             print("Success! Blog 1 not found (filters worked but no result)")
    except Exception:
        print("ORM Query Failed!")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_trace()
