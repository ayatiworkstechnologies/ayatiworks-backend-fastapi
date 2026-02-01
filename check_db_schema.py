
from app.database import SessionLocal, engine
from sqlalchemy import text, inspect

def check_schema():
    inspector = inspect(engine)
    columns = inspector.get_columns('blogs')
    print("Columns in 'blogs' table:")
    found_faqs = False
    for col in columns:
        print(f"- {col['name']} ({col['type']})")
        if col['name'] == 'faqs':
            found_faqs = True
    
    if found_faqs:
        print("\n✅ 'faqs' column FOUND.")
    else:
        print("\n❌ 'faqs' column NOT FOUND.")

if __name__ == "__main__":
    check_schema()
