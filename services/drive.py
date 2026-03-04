"""Google Drive integration service."""

import os
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

load_dotenv()

# Strip any stray CR/LF characters that Windows CRLF .env files can introduce
GOOGLE_DRIVE_FOLDER_ID = (os.getenv("GOOGLE_DRIVE_FOLDER_ID") or "").strip()

SCOPES = ["https://www.googleapis.com/auth/drive"]

# Path to the credentials and token files
CREDS_DIR = Path(__file__).resolve().parents[1]
# Inside Docker: token lives in the named-volume directory /app/token_store
# Locally:       token lives alongside credentials.json in the project root
if os.getenv("DOCKER_ENV") == "1":
    TOKEN_PATH = Path("/app/token_store/token.json")
else:
    TOKEN_PATH = CREDS_DIR / "token.json"
CREDENTIALS_PATH = CREDS_DIR / "credentials.json"


def _get_drive_service():
    """Authenticate via OAuth 2.0 to get full read/write access.

    Requires a valid token.json to already exist (generated outside of Docker
    via the one-time local setup script). Token refresh is handled automatically.
    This function will NEVER attempt to open a browser — it is headless-safe.
    """
    creds = None
    if TOKEN_PATH.exists() and TOKEN_PATH.stat().st_size > 0:
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Headless-safe: refresh the token using the stored refresh_token
            creds.refresh(Request())
            with open(TOKEN_PATH, "w") as token:
                token.write(creds.to_json())
        else:
            raise RuntimeError(
                f"No valid Google OAuth token found at {TOKEN_PATH}.\n"
                "Run the one-time local auth script to generate it:\n\n"
                "  python scripts/generate_token.py\n\n"
                "Then copy the produced token.json into the Docker volume:\n"
                "  docker cp token.json bookgateway:/app/token_store/token.json"
            )

    return build("drive", "v3", credentials=creds)


def list_books() -> list[dict]:
    """Return all PDF books in the configured folder as [{"id": ..., "name": ...}]."""
    service = _get_drive_service()
    query = (
        f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents"
        " and mimeType='application/pdf'"
        " and trashed=false"
    )
    try:
        results = (
            service.files()
            .list(q=query, fields="files(id, name)", pageSize=100)
            .execute()
        )
    except HttpError as exc:
        if exc.resp.status == 404:
            raise FileNotFoundError(
                f"Drive folder not found (id={GOOGLE_DRIVE_FOLDER_ID!r}). "
                "Check GOOGLE_DRIVE_FOLDER_ID in .env."
            ) from exc
        raise
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
    """Download a PDF from Drive by file ID to dest_path.

    Raises FileNotFoundError if the file has been deleted from Drive.
    """
    service = _get_drive_service()
    request = service.files().get_media(fileId=file_id)

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(dest_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
    except HttpError as exc:
        if exc.resp.status == 404:
            # Clean up the empty file we just created
            dest_path.unlink(missing_ok=True)
            raise FileNotFoundError(
                f"Book {file_id!r} no longer exists in Drive (deleted?)."
            ) from exc
        raise


def rename_file(file_id: str, new_name: str) -> None:
    """Rename a file in Google Drive via the OAuth 2.0 API."""
    service = _get_drive_service()
    body = {"name": f"{new_name}.pdf"}
    service.files().update(fileId=file_id, body=body).execute()
