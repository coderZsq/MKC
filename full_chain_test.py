#!/usr/bin/env python3
"""Full-chain PDF upload-and-parse test: web -> gateway -> ai."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

GATEWAY = "http://localhost:8080"
PDF_PATH = Path("resources/00-发刊词｜心有困惑时，就读王阳明.pdf")
EMAIL = "test-pdf@example.com"
PASSWORD = "Test1234"


def _request(
    method: str, path: str, body: bytes | None = None, headers: dict | None = None
) -> dict:
    req = urllib.request.Request(f"{GATEWAY}{path}", data=body, method=method)
    req.add_header("Accept", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {text}")
        raise


def _safe_request(
    method: str, path: str, body: bytes | None = None, headers: dict | None = None
) -> tuple[dict, int]:
    """Return (parsed_json, status_code), reading error body safely."""
    req = urllib.request.Request(f"{GATEWAY}{path}", data=body, method=method)
    req.add_header("Accept", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8")), resp.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body), exc.code
        except json.JSONDecodeError:
            return {"raw": body}, exc.code


def register_or_login() -> str:
    # Try login first since the test user likely exists.
    resp, status = _safe_request(
        "POST",
        "/api/v1/auth/login",
        body=json.dumps({"email": EMAIL, "password": PASSWORD}).encode(),
        headers={"Content-Type": "application/json"},
    )
    if status == 200 and resp.get("success"):
        return resp["data"]["access_token"]

    # Login failed, register the user.
    resp, status = _safe_request(
        "POST",
        "/api/v1/auth/register",
        body=json.dumps(
            {"email": EMAIL, "password": PASSWORD, "nickname": "PDF Tester"}
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    if status in (200, 201) and resp.get("success"):
        return resp["data"]["access_token"]
    if status == 409 or resp.get("error", {}).get("code") == "CONFLICT":
        resp, status = _safe_request(
            "POST",
            "/api/v1/auth/login",
            body=json.dumps({"email": EMAIL, "password": PASSWORD}).encode(),
            headers={"Content-Type": "application/json"},
        )
        if status == 200 and resp.get("success"):
            return resp["data"]["access_token"]
    raise RuntimeError(f"auth failed: {status} {resp}")


def upload_pdf(token: str) -> dict:
    boundary = f"----WebKitFormBoundary{uuid4().hex}"
    filename = PDF_PATH.name.encode("utf-8")
    file_bytes = PDF_PATH.read_bytes()
    body = (
        b"--" + boundary.encode() + b"\r\n"
        b'Content-Disposition: form-data; name="file"; filename="' + filename + b'"\r\n'
        b"Content-Type: application/pdf\r\n\r\n"
        + file_bytes
        + b"\r\n--"
        + boundary.encode()
        + b"--\r\n"
    )
    req = urllib.request.Request(
        f"{GATEWAY}/api/v1/files/upload",
        data=body,
        method="POST",
    )
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(
            f"Upload response: {resp.status} {json.dumps(data, ensure_ascii=False)[:500]}"
        )
        return data["data"]


def poll_task(token: str, task_id: str, timeout: int = 180) -> dict:
    for i in range(timeout):
        data = _request(
            "GET",
            f"/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        task = data["data"]
        status = task["status"]
        progress = task.get("progress", 0)
        print(f"[{i}s] task {task_id}: status={status}, progress={progress}")
        if status in ("completed", "failed"):
            return task
        time.sleep(1)
    raise TimeoutError(f"task {task_id} did not complete within {timeout}s")


def get_result(token: str, task_id: str) -> dict | None:
    data = _request(
        "GET", f"/api/v1/tasks/{task_id}", headers={"Authorization": f"Bearer {token}"}
    )
    return data.get("data", {}).get("result")


def main() -> int:
    if not PDF_PATH.exists():
        print(f"PDF not found: {PDF_PATH}")
        return 1

    token = register_or_login()
    print(f"Logged in, token prefix: {token[:20]}...")

    upload_result = upload_pdf(token)
    task_id = upload_result["task_id"]
    resource_id = upload_result["resource_id"]
    print(f"Uploaded: resource_id={resource_id}, task_id={task_id}")

    task = poll_task(token, task_id)
    if task["status"] == "failed":
        print(f"Task failed: {task}")
        return 1

    result = get_result(token, task_id)
    if result is None:
        print("No result available")
        return 1

    print(f"Parse succeeded: {len(result.get('pages', []))} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
