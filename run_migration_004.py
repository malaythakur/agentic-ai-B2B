"""
Run migration 004 - Add provider opt-in fields
This script adds the new columns to the service_providers table
"""

from app.database import engine
from sqlalchemy import text, inspect

def run_migration():
    """Add provider opt-in consent fields to service_providers table"""
    
    # Check if columns already exist
    inspector = inspect(engine)
    existing_columns = [col['name'] for col in inspector.get_columns('service_providers')]
    
    columns_to_add = [
        ('auto_outreach_enabled', 'BOOLEAN DEFAULT FALSE'),
        ('outreach_consent_status', 'VARCHAR(50) DEFAULT \'pending\''),
        ('outreach_consent_date', 'TIMESTAMP WITH TIME ZONE'),
        ('opt_in_email_sent_at', 'TIMESTAMP WITH TIME ZONE'),
        ('provider_response_received_at', 'TIMESTAMP WITH TIME ZONE'),
        ('provider_response_text', 'TEXT'),
        ('sentiment_analysis_result', 'JSONB'),
        ('automation_settings', 'JSONB DEFAULT \'{}\'::jsonb')
    ]
    
    with engine.connect() as conn:
        for column_name, column_def in columns_to_add:
            if column_name not in existing_columns:
                try:
                    sql = f"ALTER TABLE service_providers ADD COLUMN {column_name} {column_def}"
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"✅ Added column: {column_name}")
                except Exception as e:
                    print(f"❌ Failed to add column {column_name}: {e}")
            else:
                print(f"⏭️  Column already exists: {column_name}")
    
    print("\nMigration completed!")

if __name__ == "__main__":
    run_migration()
