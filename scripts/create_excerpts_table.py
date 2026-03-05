"""One-time script to create the excerpts table in Supabase."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load env first
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Add parent directory to path so we can import services
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.db import get_db

def create_excerpts_table():
    """Create the excerpts table with foreign key to renamed_books."""
    db = get_db()
    
    # SQL to create the table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS public.excerpts (
      id BIGSERIAL PRIMARY KEY,
      google_drive_file_id TEXT NOT NULL,
      start_page INTEGER NOT NULL,
      end_page INTEGER NOT NULL,
      has_been_studied BOOLEAN NOT NULL DEFAULT false,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      CONSTRAINT excerpts_file_id_fkey FOREIGN KEY (google_drive_file_id) 
        REFERENCES public.renamed_books(file_id) 
        ON DELETE CASCADE
    );
    """
    
    # SQL to create indexes for better performance
    create_indexes_sql = """
    CREATE INDEX IF NOT EXISTS idx_excerpts_file_id ON public.excerpts(google_drive_file_id);
    CREATE INDEX IF NOT EXISTS idx_excerpts_studied ON public.excerpts(has_been_studied);
    """
    
    print("❌ Error: Supabase Python client doesn't support raw SQL execution directly.")
    print("\nPlease run this SQL manually in the Supabase SQL Editor:\n")
    print("="*70)
    print(create_table_sql)
    print(create_indexes_sql)
    print("="*70)
    print("\nAfter running the SQL, the table will be ready for use.")
    
    return False

if __name__ == "__main__":
    create_excerpts_table()
