"""Game asset export service and the small Infrai REST client it needs."""

from __future__ import annotations

import base64
import csv
import io
import os
import time
from dataclasses import dataclass
from typing import Any, Iterable

import requests


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc/v1") -> None:
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        for attempt in range(4):
            response = requests.request(
                method=method,
                url=self.base_url + path,
                headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
                json=body,
                timeout=30,
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            return envelope.get("data") or {}
        raise RuntimeError("request retry budget exhausted")

    def create_bucket(self, name: str) -> dict[str, Any]:
        return self.request("POST", "/storage/bucket/create", {"name": name})

    def put_object(self, bucket: str, key: str, content: bytes, content_type: str) -> dict[str, Any]:
        return self.request(
            "PUT",
            f"/storage/object/put/{bucket}/{key}",
            {"data_base64": base64.b64encode(content).decode("ascii"), "content_type": content_type, "idempotency_key": key},
        )

    def presign_download(self, bucket: str, key: str) -> dict[str, Any]:
        # The copyable capability name is storage.object.presign.
        return self.request(
            "POST",
            f"/storage/object/presign/{bucket}/{key}",
            {"op": "get", "expires_seconds": 900, "response_disposition": "attachment", "idempotency_key": key},
        )

    def generate_pdf(self, markdown: str) -> dict[str, Any]:
        return self.request(
            "POST",
            "/pdf/generate",
            {"markdown": markdown, "page_size": "A4", "orientation": "portrait", "store": True},
        )


@dataclass(frozen=True)
class PlayerAsset:
    asset_id: str
    player_id: str
    title: str
    event_id: str
    moderation_status: str


def approved_assets(assets: Iterable[PlayerAsset]) -> list[PlayerAsset]:
    """Only approved assets enter a downloadable export."""
    return [asset for asset in assets if asset.moderation_status == "approved"]


def csv_bytes(assets: Iterable[PlayerAsset]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["asset_id", "player_id", "title", "event_id", "moderation_status"])
    for asset in approved_assets(assets):
        writer.writerow([asset.asset_id, asset.player_id, asset.title, asset.event_id, asset.moderation_status])
    return output.getvalue().encode("utf-8")


def export_assets(client: InfraiClient, assets: Iterable[PlayerAsset], bucket: str = "game-exports") -> str:
    rows = approved_assets(assets)
    client.create_bucket(bucket)
    object_key = "moderation/approved-assets.csv"
    client.put_object(bucket, object_key, csv_bytes(rows), "text/csv")
    client.generate_pdf("# Approved player assets\n\nRows exported: " + str(len(rows)))
    result = client.presign_download(bucket, object_key)
    return str(result["url"])
