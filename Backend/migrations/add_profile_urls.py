"""
Migration script to add profile URL columns to the resumes table.
Run this script to update your existing database.
"""
from sqlalchemy import create_engine, text
from Backend.database import SQLALCHEMY_DATABASE_URL

def migrate():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as conn:
        # Add new columns if they don't exist
        try:
            conn.execute(text("""
                ALTER TABLE resumes 
                ADD COLUMN linkedin_url VARCHAR NULL
            """))
            print("✓ Added linkedin_url column")
        except Exception as e:
            print(f"linkedin_url column might already exist: {e}")
        
        try:
            conn.execute(text("""
                ALTER TABLE resumes 
                ADD COLUMN github_url VARCHAR NULL
            """))
            print("✓ Added github_url column")
        except Exception as e:
            print(f"github_url column might already exist: {e}")
        
        try:
            conn.execute(text("""
                ALTER TABLE resumes 
                ADD COLUMN leetcode_url VARCHAR NULL
            """))
            print("✓ Added leetcode_url column")
        except Exception as e:
            print(f"leetcode_url column might already exist: {e}")
        
        conn.commit()
        print("\n✓ Migration completed successfully!")

if __name__ == "__main__":
    migrate()
