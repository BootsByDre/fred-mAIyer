"""CLI entry point for fred-mAIyer."""

from __future__ import annotations

import asyncio
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fred_maiyer.auth import (
    DEFAULT_REDIRECT_URI,
    AuthError,
    build_authorization_url,
    exchange_auth_code,
    get_client_token,
)
from fred_maiyer.store import StoreError, find_stores

ENV_PATH = Path(".env")


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2 or sys.argv[1] != "init":
        print("Usage: fred-maiyer init")
        sys.exit(1)
    _run_init()


def _run_init() -> None:
    """Run the interactive initialization wizard."""
    print()
    print("  fred-mAIyer Setup")
    print("  =================")

    if ENV_PATH.exists():
        print()
        print("  .env already exists.")
        answer = input("  Overwrite? [y/N]: ").strip().lower()
        if answer != "y":
            print("  Aborted.")
            return

    # Step 1: API credentials
    client_id, client_secret = _prompt_credentials()

    print()
    print("  Verifying credentials...", end=" ", flush=True)
    try:
        client_token = asyncio.run(get_client_token(client_id, client_secret))
        print("OK!")
    except AuthError as e:
        print("FAILED")
        print(f"  {e}")
        sys.exit(1)

    # Step 2: OAuth2 user authorization
    access_token, refresh_token = _run_oauth_flow(client_id, client_secret)

    # Step 3: Store selection
    store_id = _select_store(client_token.access_token)

    # Write config
    _write_env(client_id, client_secret, access_token, refresh_token, store_id)

    print()
    print("  Setup complete! Configuration saved to .env")
    print()


def _prompt_credentials() -> tuple[str, str]:
    print()
    print("  Step 1: Kroger API Credentials")
    print()
    print("  You need a Kroger developer account.")
    print("  1. Go to https://developer.kroger.com")
    print("  2. Create a new application")
    print(f"  3. Set the redirect URI to: {DEFAULT_REDIRECT_URI}")
    print("  4. Note your Client ID and Client Secret")
    print()
    client_id = input("  Client ID: ").strip()
    client_secret = input("  Client Secret: ").strip()
    if not client_id or not client_secret:
        print("  Error: Both Client ID and Client Secret are required.")
        sys.exit(1)
    return client_id, client_secret


def _run_oauth_flow(client_id: str, client_secret: str) -> tuple[str, str]:
    print()
    print("  Step 2: Connect Your Fred Meyer Account")
    print()

    auth_url = build_authorization_url(client_id)

    server = _start_callback_server()
    if server:
        print("  Opening your browser to authorize fred-mAIyer...")
        print(f"  (If it doesn't open, visit: {auth_url})")
        webbrowser.open(auth_url)
        print()
        print("  Waiting for authorization...", flush=True)

        # Wait up to 5 minutes for the callback
        _CallbackHandler.event.wait(timeout=300)
        server.shutdown()
        auth_code = _CallbackHandler.auth_code
    else:
        # Port unavailable — manual fallback
        print("  Visit this URL to authorize:")
        print(f"  {auth_url}")
        print()
        print("  After authorizing, you'll be redirected to a localhost URL.")
        print("  Copy the 'code' parameter from that URL.")
        print()
        auth_code = input("  Authorization code: ").strip()

    if not auth_code:
        print("  Error: No authorization code received.")
        sys.exit(1)

    print("  Exchanging authorization code...", end=" ", flush=True)
    try:
        token = asyncio.run(exchange_auth_code(client_id, client_secret, auth_code))
        print("OK!")
    except AuthError as e:
        print("FAILED")
        print(f"  {e}")
        sys.exit(1)

    return token.access_token, token.refresh_token


class _CallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler that captures the OAuth2 callback code."""

    auth_code: str | None = None
    event = threading.Event()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/callback":
            params = parse_qs(parsed.query)
            code = params.get("code", [None])[0]
            if code:
                _CallbackHandler.auth_code = code
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<h1>Authorization successful!</h1>"
                    b"<p>You can close this window.</p>"
                )
                _CallbackHandler.event.set()
                return
        self.send_response(400)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass  # suppress server logs


def _start_callback_server() -> HTTPServer | None:
    """Start a local server to catch the OAuth2 redirect.

    Returns None if the port is unavailable.
    """
    try:
        server = HTTPServer(("localhost", 8888), _CallbackHandler)
    except OSError:
        return None
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _select_store(access_token: str) -> str:
    print()
    print("  Step 3: Select Your Store")
    print()
    zip_code = input("  ZIP code: ").strip()

    print("  Searching for nearby Fred Meyer stores...", flush=True)
    try:
        stores = asyncio.run(find_stores(zip_code, access_token))
    except StoreError as e:
        print(f"  Error: {e}")
        sys.exit(1)

    if not stores:
        print("  No Fred Meyer stores found near that ZIP code.")
        store_id = input("  Enter a store ID manually: ").strip()
        return store_id

    print()
    for i, store in enumerate(stores, 1):
        print(f"    {i}. {store.name} ({store.address})")
    print()

    choice = input("  Select a store [1]: ").strip() or "1"
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(stores):
            return stores[idx].location_id
    except ValueError:
        pass

    print("  Invalid selection.")
    sys.exit(1)


def _write_env(
    client_id: str,
    client_secret: str,
    access_token: str,
    refresh_token: str,
    store_id: str,
) -> None:
    """Write configuration to .env file."""
    ENV_PATH.write_text(
        f"KROGER_CLIENT_ID={client_id}\n"
        f"KROGER_CLIENT_SECRET={client_secret}\n"
        f"KROGER_ACCESS_TOKEN={access_token}\n"
        f"KROGER_REFRESH_TOKEN={refresh_token}\n"
        f"KROGER_STORE_ID={store_id}\n"
    )
