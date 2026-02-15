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
from fred_maiyer.google_tasks import (
    DEFAULT_GOOGLE_REDIRECT_URI,
    GoogleTasksError,
    build_google_auth_url,
    exchange_google_auth_code,
    list_task_lists,
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

    # Step 4 (optional): Google Tasks shopping list
    google_config = _setup_google_tasks()

    # Write config
    _write_env(
        client_id, client_secret, access_token, refresh_token, store_id, google_config
    )

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


class GoogleConfig:
    """Holds optional Google Tasks configuration."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: str,
        refresh_token: str,
        list_id: str,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.list_id = list_id


def _setup_google_tasks() -> GoogleConfig | None:
    """Optionally set up Google Tasks as a shopping list source."""
    print()
    print("  Step 4: Google Tasks Shopping List (Optional)")
    print()
    print("  You can connect a Google Tasks list to use as your shopping list.")
    print("  When starting an order, items will be pulled from that list.")
    print("  After adding them to your cart, they'll be checked off automatically.")
    print()
    answer = input("  Set up Google Tasks? [y/N]: ").strip().lower()
    if answer != "y":
        print("  Skipped.")
        return None

    print()
    print("  You need Google Cloud OAuth2 credentials with the Tasks API enabled.")
    print("  1. Go to https://console.cloud.google.com/apis/credentials")
    print("  2. Create an OAuth 2.0 Client ID (Desktop or Web app)")
    print(f"  3. Add {DEFAULT_GOOGLE_REDIRECT_URI} as an authorized redirect URI")
    print("  4. Enable the Google Tasks API for your project")
    print()

    g_client_id = input("  Google Client ID: ").strip()
    g_client_secret = input("  Google Client Secret: ").strip()
    if not g_client_id or not g_client_secret:
        print("  Error: Both Client ID and Client Secret are required.")
        print("  Skipping Google Tasks setup.")
        return None

    # OAuth2 flow for Google
    g_access_token, g_refresh_token = _run_google_oauth_flow(
        g_client_id, g_client_secret
    )

    # Select a task list
    list_id = _select_task_list(g_access_token)

    return GoogleConfig(
        client_id=g_client_id,
        client_secret=g_client_secret,
        access_token=g_access_token,
        refresh_token=g_refresh_token,
        list_id=list_id,
    )


def _run_google_oauth_flow(client_id: str, client_secret: str) -> tuple[str, str]:
    """Run the Google OAuth2 flow to get user tokens."""
    print()
    print("  Connecting your Google account...")
    print()

    auth_url = build_google_auth_url(client_id)

    server = _start_google_callback_server()
    if server:
        print("  Opening your browser to authorize Google Tasks access...")
        print(f"  (If it doesn't open, visit: {auth_url})")
        webbrowser.open(auth_url)
        print()
        print("  Waiting for authorization...", flush=True)

        _GoogleCallbackHandler.event.wait(timeout=300)
        server.shutdown()
        auth_code = _GoogleCallbackHandler.auth_code
    else:
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

    print("  Exchanging Google authorization code...", end=" ", flush=True)
    try:
        token = asyncio.run(
            exchange_google_auth_code(client_id, client_secret, auth_code)
        )
        print("OK!")
    except GoogleTasksError as e:
        print("FAILED")
        print(f"  {e}")
        sys.exit(1)

    return token.access_token, token.refresh_token


class _GoogleCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler that captures the Google OAuth2 callback code."""

    auth_code: str | None = None
    event = threading.Event()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/callback":
            params = parse_qs(parsed.query)
            code = params.get("code", [None])[0]
            if code:
                _GoogleCallbackHandler.auth_code = code
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<h1>Google authorization successful!</h1>"
                    b"<p>You can close this window.</p>"
                )
                _GoogleCallbackHandler.event.set()
                return
        self.send_response(400)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        pass


def _start_google_callback_server() -> HTTPServer | None:
    """Start a local server on port 8889 for the Google OAuth2 redirect."""
    try:
        server = HTTPServer(("localhost", 8889), _GoogleCallbackHandler)
    except OSError:
        return None
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _select_task_list(access_token: str) -> str:
    """Let the user pick a Google Tasks list to use as their shopping list."""
    print()
    print("  Fetching your Google Tasks lists...", flush=True)
    try:
        task_lists = asyncio.run(list_task_lists(access_token))
    except GoogleTasksError as e:
        print(f"  Error: {e}")
        sys.exit(1)

    if not task_lists:
        print("  No task lists found in your Google account.")
        list_id = input("  Enter a task list ID manually: ").strip()
        return list_id

    print()
    for i, tl in enumerate(task_lists, 1):
        print(f"    {i}. {tl.title}")
    print()

    choice = input("  Select a list [1]: ").strip() or "1"
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(task_lists):
            print(f"  Selected: {task_lists[idx].title}")
            return task_lists[idx].id
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
    google_config: GoogleConfig | None = None,
) -> None:
    """Write configuration to .env file."""
    content = (
        f"KROGER_CLIENT_ID={client_id}\n"
        f"KROGER_CLIENT_SECRET={client_secret}\n"
        f"KROGER_ACCESS_TOKEN={access_token}\n"
        f"KROGER_REFRESH_TOKEN={refresh_token}\n"
        f"KROGER_STORE_ID={store_id}\n"
    )
    if google_config:
        content += (
            f"\n# Google Tasks shopping list\n"
            f"GOOGLE_CLIENT_ID={google_config.client_id}\n"
            f"GOOGLE_CLIENT_SECRET={google_config.client_secret}\n"
            f"GOOGLE_ACCESS_TOKEN={google_config.access_token}\n"
            f"GOOGLE_REFRESH_TOKEN={google_config.refresh_token}\n"
            f"GOOGLE_TASKS_LIST_ID={google_config.list_id}\n"
        )
    ENV_PATH.write_text(content)
