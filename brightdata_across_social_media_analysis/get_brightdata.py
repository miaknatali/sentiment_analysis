import os
import json
import time
from pathlib import Path

import requests


API_KEY = os.getenv("BRIGHTDATA_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

DATASET = {
    "platform_name": "instagram",
    "dataset_id": "gd_lk5ns7kz21pck8jpis",
    "records_limit": 21700,
    "field": "description",
}


def build_filter(field: str) -> dict:
    return {
        "operator": "or",
        "filters": [
            {"name": field, "value": "data center", "operator": "includes"},
            {"name": field, "value": "datacenter", "operator": "includes"},
            {"name": field, "value": "data centre", "operator": "includes"},
            {"name": field, "value": "datacentre", "operator": "includes"},
            # Max 4 rules
            # {"name": field, "value": "server farm", "operator": "includes"},
            # {"name": field, "value": "colocation facility", "operator": "includes"},
            # {"name": field, "value": "colo facility", "operator": "includes"},
            # {"name": field, "value": "hyperscale data center", "operator": "includes"},
            # {"name": field, "value": "hyperscaler", "operator": "includes"},
        ],
    }


def create_snapshot(dataset_id: str, records_limit: int, field: str) -> str:
    url = "https://api.brightdata.com/datasets/filter"

    payload = {
        "dataset_id": dataset_id,
        "records_limit": records_limit,
        "filter": build_filter(field),
    }

    print("\nCreating snapshot with payload:")
    print(json.dumps(payload, indent=2))

    response = requests.post(
        url,
        headers=HEADERS,
        json=payload,
        timeout=60,
    )

    print(f"Create snapshot status code: {response.status_code}")

    try:
        response_data = response.json()
        print("Create snapshot response:")
        print(json.dumps(response_data, indent=2))
    except json.JSONDecodeError:
        print("Create snapshot raw response:")
        print(response.text)
        response.raise_for_status()
        raise

    response.raise_for_status()

    snapshot_id = response_data.get("snapshot_id") or response_data.get("id")

    if not snapshot_id:
        raise RuntimeError(f"No snapshot_id found in response: {response_data}")

    return snapshot_id


def get_snapshot_metadata(snapshot_id: str) -> dict:
    url = f"https://api.brightdata.com/datasets/snapshots/{snapshot_id}"

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=60,
    )

    print(f"Metadata status code: {response.status_code}")

    try:
        metadata = response.json()
    except json.JSONDecodeError:
        print("Metadata raw response:")
        print(response.text)
        response.raise_for_status()
        raise

    response.raise_for_status()

    return metadata


def wait_for_snapshot_ready(snapshot_id: str, max_attempts: int = 30, sleep_seconds: int = 10) -> dict:
    for attempt in range(1, max_attempts + 1):
        metadata = get_snapshot_metadata(snapshot_id)

        print("Snapshot metadata:")
        print(json.dumps(metadata, indent=2))

        status = metadata.get("status")

        if status == "ready":
            print(f"Snapshot {snapshot_id} is ready.")
            return metadata

        if status in {"failed", "cancelled", "canceled"}:
            raise RuntimeError(f"Snapshot {snapshot_id} ended with status {status}: {metadata}")

        print(f"Snapshot not ready yet. Status: {status}. Attempt {attempt}/{max_attempts}.")
        time.sleep(sleep_seconds)

    raise TimeoutError(
        f"Snapshot {snapshot_id} did not become ready after "
        f"{max_attempts * sleep_seconds} seconds."
    )


def main():
    platform_name = DATASET["platform_name"]

    print("\n" + "=" * 80)
    print(f"Starting platform: {platform_name}")
    print("=" * 80)

    snapshot_id = create_snapshot(
        dataset_id=DATASET["dataset_id"],
        records_limit=DATASET["records_limit"],
        field=DATASET["field"],
    )

    print(f"Created snapshot ID for {platform_name}: {snapshot_id}")

    wait_for_snapshot_ready(snapshot_id)


if __name__ == "__main__":
    main()