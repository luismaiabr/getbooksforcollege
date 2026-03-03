"""Debug script: test Drive API directly."""
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

print(f"API_KEY  = {API_KEY}")
print(f"FOLDER_ID= {FOLDER_ID}")

service = build("drive", "v3", developerKey=API_KEY)

query = f"'{FOLDER_ID}' in parents and mimeType='application/pdf' and trashed=false"
results = service.files().list(q=query, fields="files(id, name)", pageSize=100).execute()

files = results.get("files", [])
print(f"\nRaw files response ({len(files)} files):")
for f in files:
    print(f"  {f['id']}  {f['name']}")

from services.drive import list_books
print("\nlist_books() =", list_books())
