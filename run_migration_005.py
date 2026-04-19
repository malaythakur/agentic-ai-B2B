"""
Run migration 005 - Add follow-up tracking fields
This script adds the new columns to the matches table
"""

from app.database import engine
from sqlalchemy import text, inspect

def run_migration():
    """Add follow-up tracking fields to matches table"""
    
    # Check if columns already exist
    inspector = inspect(engine)
    existing_columns = [col['name'] for col in inspector.get_columns('matches')]
    
    columns_to_add = [
        ('followup_count', 'INTEGER DEFAULT 0'),
        ('last_followup_sent_at', 'TIMESTAMP WITH TIME ZONE'),
        ('response_received', 'BOOLEAN DEFAULT FALSE'),
        ('response_received_at', 'TIMESTAMP WITH TIME ZONE')
    ]
    
    with engine.connect() as conn:
        for column_name, column_def in columns_to_add:
            if column_name not in existing_columns:
                try:
                    sql = f"ALTER TABLE matches ADD COLUMN {column_name} {column_def}"
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"✅ Added column: {column_name}")
                except Exception as e:
                    print(f"❌ Failed to add column {column_name}: {e}")
            else:
                print(f"⏭️  Column already exists: {column_name}")
    
    print("\nMigration 005 completed!")

if __name__ == "__main__":
    run_migration()
