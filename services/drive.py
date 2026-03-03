"""Google Drive integration service."""

import os
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

load_dotenv()

GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

SCOPES = ["https://www.googleapis.com/auth/drive"]

# Path to the credentials and token files (assuming they're in the project root)
CREDS_DIR = Path(__file__).resolve().parents[1]
TOKEN_PATH = CREDS_DIR / "token.json"
CREDENTIALS_PATH = CREDS_DIR / "credentials.json"


def _get_drive_service():
    """Authenticate via OAuth 2.0 to get full read/write access."""
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"OAuth credentials not found at {CREDENTIALS_PATH}. "
                    "Please download OAuth 2.0 Desktop credentials from Google Cloud Console "
                    "and place them there."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    return build("drive", "v3", credentials=creds)


def list_books() -> list[dict]:
    """Return all PDF books in the configured folder as [{"id": ..., "name": ...}]."""
    service = _get_drive_service()
    query = (
        f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents"
        " and mimeType='application/pdf'"
        " and trashed=false"
    )
    results = (
        service.files()
        .list(q=query, fields="files(id, name)", pageSize=100)
        .execute()
    )
    return [
        {"id": f["id"], "name": f["name"].removesuffix(".pdf")}
        for f in results.get("files", [])
    ]


def get_book_metadata(file_id: str) -> dict:
    """Return {"id": ..., "name": ...} for a single file ID. Raises if not found."""
    service = _get_drive_service()
    f = service.files().get(fileId=file_id, fields="id, name").execute()
    return {"id": f["id"], "name": f["name"].removesuffix(".pdf")}


def download_book(file_id: str, dest_path: Path) -> None:
    """Download a PDF from Drive by file ID to dest_path."""
    service = _get_drive_service()
    request = service.files().get_media(fileId=file_id)

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def rename_file(file_id: str, new_name: str) -> None:
    """Rename a file in Google Drive via the OAuth 2.0 API."""
    service = _get_drive_service()
    body = {"name": f"{new_name}.pdf"}
    service.files().update(fileId=file_id, body=body).execute()
