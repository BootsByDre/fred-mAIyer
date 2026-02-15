"""Google Tasks API integration for shopping list support."""

from __future__ import annotations

from urllib.parse import urlencode

import httpx

from fred_maiyer.models import GoogleTask, GoogleTaskList, TokenResponse

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TASKS_BASE_URL = "https://tasks.googleapis.com/tasks/v1"
GOOGLE_TASKS_SCOPE = "https://www.googleapis.com/auth/tasks"
DEFAULT_GOOGLE_REDIRECT_URI = "http://localhost:8889/callback"


class GoogleTasksError(Exception):
    """Raised when a Google Tasks API call fails."""


def build_google_auth_url(
    client_id: str,
    redirect_uri: str = DEFAULT_GOOGLE_REDIRECT_URI,
    scope: str = GOOGLE_TASKS_SCOPE,
) -> str:
    """Build the Google OAuth2 authorization URL for user consent."""
    params = {
        "scope": scope,
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_google_auth_code(
    client_id: str,
    client_secret: str,
    auth_code: str,
    redirect_uri: str = DEFAULT_GOOGLE_REDIRECT_URI,
) -> TokenResponse:
    """Exchange a Google authorization code for access and refresh tokens."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
            },
        )
        if response.status_code != 200:
            raise GoogleTasksError(
                f"Failed to exchange Google auth code: "
                f"{response.status_code} {response.text}"
            )
        return TokenResponse.model_validate(response.json())


async def refresh_google_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> TokenResponse:
    """Refresh an expired Google access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
            },
        )
        if response.status_code != 200:
            raise GoogleTasksError(
                f"Failed to refresh Google token: "
                f"{response.status_code} {response.text}"
            )
        return TokenResponse.model_validate(response.json())


async def list_task_lists(access_token: str) -> list[GoogleTaskList]:
    """List all Google Task lists for the authenticated user."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GOOGLE_TASKS_BASE_URL}/users/@me/lists",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code != 200:
            raise GoogleTasksError(
                f"Failed to list task lists: {response.status_code} {response.text}"
            )
        data = response.json()
        return [
            GoogleTaskList(id=item["id"], title=item["title"])
            for item in data.get("items", [])
        ]


async def get_incomplete_tasks(
    access_token: str,
    tasklist_id: str,
) -> list[GoogleTask]:
    """Get all incomplete tasks from a Google Tasks list."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GOOGLE_TASKS_BASE_URL}/lists/{tasklist_id}/tasks",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"showCompleted": "false", "showHidden": "false"},
        )
        if response.status_code != 200:
            raise GoogleTasksError(
                f"Failed to get tasks: {response.status_code} {response.text}"
            )
        data = response.json()
        return [
            GoogleTask(
                id=item["id"],
                title=item["title"],
                notes=item.get("notes", ""),
                status=item.get("status", "needsAction"),
            )
            for item in data.get("items", [])
            if item.get("status") != "completed"
        ]


async def complete_task(
    access_token: str,
    tasklist_id: str,
    task_id: str,
) -> None:
    """Mark a single task as completed in Google Tasks."""
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{GOOGLE_TASKS_BASE_URL}/lists/{tasklist_id}/tasks/{task_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={"status": "completed"},
        )
        if response.status_code != 200:
            raise GoogleTasksError(
                f"Failed to complete task {task_id}: "
                f"{response.status_code} {response.text}"
            )


async def complete_tasks(
    access_token: str,
    tasklist_id: str,
    task_ids: list[str],
) -> None:
    """Mark multiple tasks as completed in Google Tasks."""
    async with httpx.AsyncClient() as client:
        for task_id in task_ids:
            response = await client.patch(
                f"{GOOGLE_TASKS_BASE_URL}/lists/{tasklist_id}/tasks/{task_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"status": "completed"},
            )
            if response.status_code != 200:
                raise GoogleTasksError(
                    f"Failed to complete task {task_id}: "
                    f"{response.status_code} {response.text}"
                )
