
from app.database import engine
from sqlalchemy import text

def fix_schema():
    with engine.connect() as connection:
        try:
            print("Adding 'faqs' column to 'blogs' table...")
            connection.execute(text("ALTER TABLE blogs ADD COLUMN faqs JSON"))
            connection.commit()
            print("✅ 'faqs' column added successfully.")
        except Exception as e:
            print(f"❌ Failed to add column: {e}")

if __name__ == "__main__":
    fix_schema()
