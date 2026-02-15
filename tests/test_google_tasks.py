"""Tests for the Google Tasks module."""

import respx
from httpx import Response

from fred_maiyer.google_tasks import (
    GoogleTasksError,
    build_google_auth_url,
    complete_task,
    complete_tasks,
    exchange_google_auth_code,
    get_incomplete_tasks,
    list_task_lists,
    refresh_google_token,
)


def test_build_google_auth_url():
    url = build_google_auth_url("google-client-id")
    assert "accounts.google.com" in url
    assert "client_id=google-client-id" in url
    assert "response_type=code" in url
    assert "access_type=offline" in url
    assert "tasks" in url


def test_build_google_auth_url_custom_redirect():
    url = build_google_auth_url(
        "google-client-id", redirect_uri="http://example.com/cb"
    )
    assert "example.com" in url


@respx.mock
async def test_exchange_google_auth_code():
    respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=Response(
            200,
            json={
                "access_token": "google-token",
                "refresh_token": "google-refresh",
                "token_type": "Bearer",
                "expires_in": 3600,
            },
        )
    )
    token = await exchange_google_auth_code(
        "g-client-id", "g-client-secret", "auth-code"
    )
    assert token.access_token == "google-token"
    assert token.refresh_token == "google-refresh"


@respx.mock
async def test_exchange_google_auth_code_failure():
    respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=Response(400, text="Bad Request")
    )
    try:
        await exchange_google_auth_code("g-client-id", "g-client-secret", "bad-code")
        assert False, "Expected GoogleTasksError"
    except GoogleTasksError:
        pass


@respx.mock
async def test_refresh_google_token():
    respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=Response(
            200,
            json={
                "access_token": "refreshed-google-token",
                "token_type": "Bearer",
                "expires_in": 3600,
            },
        )
    )
    token = await refresh_google_token("g-client-id", "g-client-secret", "old-refresh")
    assert token.access_token == "refreshed-google-token"


@respx.mock
async def test_refresh_google_token_failure():
    respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=Response(401, text="Unauthorized")
    )
    try:
        await refresh_google_token("g-client-id", "g-client-secret", "bad-refresh")
        assert False, "Expected GoogleTasksError"
    except GoogleTasksError:
        pass


@respx.mock
async def test_list_task_lists(access_token: str):
    respx.get("https://tasks.googleapis.com/tasks/v1/users/@me/lists").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {"id": "list-1", "title": "Shopping List"},
                    {"id": "list-2", "title": "My Tasks"},
                ]
            },
        )
    )
    lists = await list_task_lists(access_token)
    assert len(lists) == 2
    assert lists[0].id == "list-1"
    assert lists[0].title == "Shopping List"
    assert lists[1].id == "list-2"


@respx.mock
async def test_list_task_lists_failure(access_token: str):
    respx.get("https://tasks.googleapis.com/tasks/v1/users/@me/lists").mock(
        return_value=Response(401, text="Unauthorized")
    )
    try:
        await list_task_lists(access_token)
        assert False, "Expected GoogleTasksError"
    except GoogleTasksError:
        pass


@respx.mock
async def test_get_incomplete_tasks(access_token: str):
    respx.get("https://tasks.googleapis.com/tasks/v1/lists/list-1/tasks").mock(
        return_value=Response(
            200,
            json={
                "items": [
                    {
                        "id": "task-1",
                        "title": "Milk",
                        "notes": "Whole milk, 1 gallon",
                        "status": "needsAction",
                    },
                    {
                        "id": "task-2",
                        "title": "Eggs",
                        "status": "needsAction",
                    },
                    {
                        "id": "task-3",
                        "title": "Already done",
                        "status": "completed",
                    },
                ]
            },
        )
    )
    tasks = await get_incomplete_tasks(access_token, "list-1")
    assert len(tasks) == 2
    assert tasks[0].id == "task-1"
    assert tasks[0].title == "Milk"
    assert tasks[0].notes == "Whole milk, 1 gallon"
    assert tasks[1].id == "task-2"
    assert tasks[1].title == "Eggs"
    assert tasks[1].notes == ""


@respx.mock
async def test_get_incomplete_tasks_empty(access_token: str):
    respx.get("https://tasks.googleapis.com/tasks/v1/lists/list-1/tasks").mock(
        return_value=Response(200, json={})
    )
    tasks = await get_incomplete_tasks(access_token, "list-1")
    assert tasks == []


@respx.mock
async def test_get_incomplete_tasks_failure(access_token: str):
    respx.get("https://tasks.googleapis.com/tasks/v1/lists/list-1/tasks").mock(
        return_value=Response(500, text="Server Error")
    )
    try:
        await get_incomplete_tasks(access_token, "list-1")
        assert False, "Expected GoogleTasksError"
    except GoogleTasksError:
        pass


@respx.mock
async def test_complete_task(access_token: str):
    respx.patch("https://tasks.googleapis.com/tasks/v1/lists/list-1/tasks/task-1").mock(
        return_value=Response(
            200,
            json={
                "id": "task-1",
                "title": "Milk",
                "status": "completed",
            },
        )
    )
    await complete_task(access_token, "list-1", "task-1")


@respx.mock
async def test_complete_task_failure(access_token: str):
    respx.patch("https://tasks.googleapis.com/tasks/v1/lists/list-1/tasks/task-1").mock(
        return_value=Response(404, text="Not Found")
    )
    try:
        await complete_task(access_token, "list-1", "task-1")
        assert False, "Expected GoogleTasksError"
    except GoogleTasksError:
        pass


@respx.mock
async def test_complete_tasks(access_token: str):
    respx.patch("https://tasks.googleapis.com/tasks/v1/lists/list-1/tasks/task-1").mock(
        return_value=Response(200, json={"id": "task-1", "status": "completed"})
    )
    respx.patch("https://tasks.googleapis.com/tasks/v1/lists/list-1/tasks/task-2").mock(
        return_value=Response(200, json={"id": "task-2", "status": "completed"})
    )
    await complete_tasks(access_token, "list-1", ["task-1", "task-2"])


@respx.mock
async def test_complete_tasks_partial_failure(access_token: str):
    respx.patch("https://tasks.googleapis.com/tasks/v1/lists/list-1/tasks/task-1").mock(
        return_value=Response(200, json={"id": "task-1", "status": "completed"})
    )
    respx.patch("https://tasks.googleapis.com/tasks/v1/lists/list-1/tasks/task-2").mock(
        return_value=Response(404, text="Not Found")
    )
    try:
        await complete_tasks(access_token, "list-1", ["task-1", "task-2"])
        assert False, "Expected GoogleTasksError"
    except GoogleTasksError:
        pass
