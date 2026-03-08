"""
Google Drive OAuth token generation script.

Can run in two modes:
1. Local mode (default): Opens browser locally, saves to project root
2. Docker/headless mode: Runs OAuth server on 0.0.0.0:8080 for remote access

Usage:
    # Local mode:
    python scripts/generate_token.py
    
    # Docker/headless mode:
    python scripts/generate_token.py --headless
    
    # Custom output path:
    python scripts/generate_token.py --output /app/token_store/token.json
"""

import argparse
import os
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS_PATH = PROJECT_ROOT / "credentials.json"

# Default token path (can be overridden via --output)
DEFAULT_TOKEN_PATH = PROJECT_ROOT / "token.json"

# Docker volume path
DOCKER_TOKEN_PATH = Path("/app/token_store/token.json")


def generate_token(output_path: Path = None, headless: bool = False) -> Path:
    """Generate OAuth token and save to specified path.
    
    Args:
        output_path: Where to save token.json (defaults to project root)
        headless: If True, run server on 0.0.0.0:8080 without opening browser
        
    Returns:
        Path where token was saved
    """
    if output_path is None:
        # Auto-detect: use Docker path if it exists, otherwise project root
        if DOCKER_TOKEN_PATH.parent.exists():
            output_path = DOCKER_TOKEN_PATH
        else:
            output_path = DEFAULT_TOKEN_PATH
    
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError(
            f"credentials.json not found at {CREDENTIALS_PATH}.\n"
            "Download OAuth 2.0 Desktop credentials from Google Cloud Console and place it there."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    
    if headless:
        # For "installed" (Desktop) OAuth clients, Google only allows
        # http://localhost as the redirect URI.  We run the callback server
        # on 0.0.0.0 inside Docker; the port is forwarded to the host,
        # and VS Code Remote SSH auto-forwards it to the developer's machine
        # so that the browser redirect to localhost:8080 reaches us.
        from wsgiref.simple_server import WSGIRequestHandler, make_server
        from urllib.parse import parse_qs

        port = 8080
        redirect_uri = f"http://localhost:{port}/"
        flow.redirect_uri = redirect_uri
        auth_url, _ = flow.authorization_url(prompt="consent")

        print("\n" + "="*70)
        print("🔐 Google Drive OAuth Authentication Required")
        print("="*70)
        print("\nOpen this URL in your browser:\n")
        print(f"   {auth_url}\n")
        print("Sign in and grant access. The browser will redirect back")
        print("automatically and this script will capture the token.\n")

        received = {}

        def _callback_app(environ, start_response):
            query = parse_qs(environ.get("QUERY_STRING", ""))
            received["code"] = query.get("code", [None])[0]
            received["error"] = query.get("error", [None])[0]
            start_response("200 OK", [("Content-Type", "text/html")])
            return [b"<html><body><h2>\xe2\x9c\x85 Authentication complete!</h2>"
                    b"<p>You can close this tab and return to the terminal.</p></body></html>"]

        class _QuietHandler(WSGIRequestHandler):
            def log_message(self, *args): pass

        print("Waiting for OAuth callback on port", port, "...")
        server = make_server("0.0.0.0", port, _callback_app, handler_class=_QuietHandler)
        server.handle_request()

        if received.get("error"):
            raise RuntimeError(f"OAuth error: {received['error']}")
        if not received.get("code"):
            raise RuntimeError("No authorization code received in callback.")

        flow.fetch_token(code=received["code"])
        creds = flow.credentials
    else:
        # Local mode: open browser automatically
        creds = flow.run_local_server(port=0)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(creds.to_json())
    
    print(f"\n✅ token.json written to {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Google Drive OAuth token")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (Docker-friendly, no browser auto-open)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for token.json (default: auto-detect)"
    )
    
    args = parser.parse_args()
    
    # Auto-detect headless mode if running in Docker
    is_docker = os.getenv("DOCKER_ENV") == "1"
    headless = args.headless or is_docker
    
    generate_token(output_path=args.output, headless=headless)
