import sys
import os
from pathlib import Path

# Add the project dir to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services import drive

def main():
    try:
        books = drive.list_books()
        print(f"Total books found: {len(books)}")
        for b in books:
            print(f"- {b['id']} | {b['folder']} | {b['name']}")
            
        print("\nNow let's check one of the missing books directly by ID.")
        missing_id = "1i7-gaeNpOnpdvNEY9AJzBpXc0IY-4LxQ" # LOGICA PARTE 2
        try:
            meta = drive.get_book_metadata(missing_id)
            print(f"Missing book meta: {meta}")
            
            # Now let's see its parents
            service = drive._get_drive_service()
            f = service.files().get(fileId=missing_id, fields="id, name, mimeType, parents").execute()
            print(f"Missing book raw details: {f}")
            
            parent_id = f.get('parents', [])[0] if f.get('parents') else None
            if parent_id:
                p = service.files().get(fileId=parent_id, fields="id, name, mimeType, parents").execute()
                print(f"Parent folder details: {p}")
                
        except Exception as e:
            print(f"Error fetching missing book: {e}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
