"""
One-time local script to generate token.json via the Google OAuth browser flow.

Run this ONCE on a machine with a browser (your local dev machine, NOT inside Docker):

    python scripts/generate_token.py

It will open a browser window for you to log in and authorise access to Google Drive.
On success it writes token.json to the project root.

Then copy it into the running Docker container:

    docker cp token.json bookgateway:/app/token_store/token.json

The container will use the refresh_token inside it from that point on — no browser needed again.
"""

from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS_PATH = PROJECT_ROOT / "credentials.json"
TOKEN_PATH = PROJECT_ROOT / "token.json"

if not CREDENTIALS_PATH.exists():
    raise FileNotFoundError(
        f"credentials.json not found at {CREDENTIALS_PATH}.\n"
        "Download OAuth 2.0 Desktop credentials from Google Cloud Console and place it there."
    )

flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
creds = flow.run_local_server(port=0)

TOKEN_PATH.write_text(creds.to_json())
print(f"\n✅ token.json written to {TOKEN_PATH}")
print("\nNow copy it into Docker:")
print("  docker cp token.json bookgateway:/app/token_store/token.json")
