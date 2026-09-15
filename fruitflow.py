#!/usr/bin/env python3
"""Keep a Buffer TikTok queue filled from a public Google Drive folder."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

API_URL = "https://api.buffer.com"
STATE_FILE = Path(__file__).with_name("fruitflow-state.json")
DRIVE_API_URL = "https://www.googleapis.com/drive/v3/files"

CAPTIONS = [
    "Wait for the ending… 🍓😱 #TalkingFruit #FruitDrama #AIStory #StoryTime #FYP",
    "This fruit chose chaos… 🍊😳 #TalkingFruit #FruitDrama #AIStory #StoryTime #FYP",
    "Nobody expected that ending… 🍎💀 #TalkingFruit #FruitDrama #AIStory #PlotTwist #FYP",
    "The fruit drama keeps getting worse… 🍇👀 #TalkingFruit #FruitDrama #AIStory #StoryTime #FYP",
]


class BufferAPI:
    def __init__(self, token: str) -> None:
        self.headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def graphql(self, query: str, variables: dict | None = None) -> dict:
        response = requests.post(API_URL, headers=self.headers, json={"query": query, "variables": variables or {}}, timeout=45)
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            raise RuntimeError(json.dumps(payload["errors"], ensure_ascii=False))
        return payload["data"]

    def account(self) -> dict:
        return self.graphql("query { account { id email timezone organizations { id name } } }")["account"]

    def channels(self, organization_id: str) -> list[dict]:
        query = """
        query Channels($input: ChannelsInput!) {
          channels(input: $input) { id name displayName service isDisconnected isLocked timezone }
        }
        """
        return self.graphql(query, {"input": {"organizationId": organization_id}})["channels"]

    def create_tiktok(self, channel_id: str, due_at: str, video_url: str, caption: str) -> dict:
        mutation = """
        mutation CreatePost($input: CreatePostInput!) {
          createPost(input: $input) {
            __typename
            ... on PostActionSuccess { post { id dueAt status schedulingType } }
            ... on MutationError { message }
          }
        }
        """
        post_input = {
            "channelId": channel_id,
            "text": caption,
            "assets": [{"video": {"url": video_url}}],
            "dueAt": due_at,
            "mode": "customScheduled",
            "schedulingType": "automatic",
            "needsApproval": False,
            "saveToDraft": False,
            "aiAssisted": True,
            "metadata": {"tiktok": {"isAiGenerated": True}},
            "source": "fruitflow",
        }
        return self.graphql(mutation, {"input": post_input})["createPost"]


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"used": [], "scheduled": []}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def video_number(name: str) -> int:
    """Return the number in names such as 'Video (264).mp4'."""
    match = re.search(r"Video\s*\((\d+)\)", name, flags=re.IGNORECASE)
    return int(match.group(1)) if match else 10**12


def list_drive_videos(folder_id: str, api_key: str) -> list[dict]:
    """List every video in a publicly shared Drive folder via Drive API v3."""
    files: list[dict] = []
    page_token = None
    while True:
        params = {
            "key": api_key,
            "q": f"'{folder_id}' in parents and trashed = false",
            "fields": "nextPageToken,files(id,name,mimeType)",
            "pageSize": 1000,
            "orderBy": "name",
        }
        if page_token:
            params["pageToken"] = page_token
        response = requests.get(DRIVE_API_URL, params=params, timeout=45)
        response.raise_for_status()
        payload = response.json()
        files.extend(
            item for item in payload.get("files", [])
            if item.get("mimeType", "").startswith("video/") or item.get("name", "").lower().endswith(".mp4")
        )
        page_token = payload.get("nextPageToken")
        if not page_token:
            break
    return sorted(files, key=lambda item: (video_number(item["name"]), item["name"].lower()))


def next_slots(times: list[str], timezone: str, count: int, occupied: set[str]) -> list[datetime]:
    tz = ZoneInfo(timezone)
    now = datetime.now(tz) + timedelta(minutes=10)
    slots: list[datetime] = []
    day = now.date()
    while len(slots) < count:
        for value in times:
            hour, minute = map(int, value.split(":"))
            candidate = datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)
            if candidate >= now and candidate.isoformat() not in occupied:
                slots.append(candidate)
                if len(slots) == count:
                    break
        day += timedelta(days=1)
    return slots


def discover(api: BufferAPI) -> None:
    account = api.account()
    print(f"Compte Buffer: {account['email']}")
    for org in account["organizations"]:
        print(f"Organisation: {org['name']} ({org['id']})")
        for channel in api.channels(org["id"]):
            print(f"  {channel['service']}: {channel['name']} -> BUFFER_CHANNEL_ID={channel['id']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["discover", "plan", "run"])
    args = parser.parse_args()
    load_dotenv(Path(__file__).with_name(".env"))
    token = os.environ.get("BUFFER_API_KEY")
    if not token:
        raise SystemExit("BUFFER_API_KEY manque dans .env")
    api = BufferAPI(token)
    if args.command == "discover":
        discover(api)
        return

    channel_id = os.environ.get("BUFFER_CHANNEL_ID")
    if not channel_id:
        raise SystemExit("Lance d’abord: python fruitflow.py discover")
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    google_api_key = os.getenv("GOOGLE_DRIVE_API_KEY", "")
    if not folder_id or not google_api_key:
        raise SystemExit("GOOGLE_DRIVE_FOLDER_ID ou GOOGLE_DRIVE_API_KEY manque dans .env")
    times = [value.strip() for value in os.getenv("POST_TIMES", "13:45,16:45,18:45,20:45").split(",") if value.strip()]
    target = int(os.getenv("QUEUE_TARGET", "10"))
    state = load_state()
    tz = ZoneInfo(os.getenv("TIMEZONE", "Europe/Paris"))
    now = datetime.now(tz)
    active = [
        {"video": item["video"], "dueAt": item["dueAt"]}
        for item in state.get("scheduled", [])
        if datetime.fromisoformat(item["dueAt"]) > now
    ]
    state["scheduled"] = active
    available = max(0, target - len(active))
    if available == 0:
        print(f"File déjà remplie: {len(active)}/{target}. Rien à ajouter.")
        if args.command == "run":
            save_state(state)
        return

    videos = list_drive_videos(folder_id, google_api_key)
    used = set(state.get("used", []))
    candidates = [item for item in videos if video_number(item["name"]) not in used][:available]
    if not candidates:
        print("Aucune nouvelle vidéo disponible dans le dossier Drive.")
        return
    occupied = {item["dueAt"] for item in active}
    slots = next_slots(times, os.getenv("TIMEZONE", "Europe/Paris"), len(candidates), occupied)

    planned = []
    for index, (item, slot) in enumerate(zip(candidates, slots)):
        number = video_number(item["name"])
        if number == 10**12:
            print(f"Ignoré (nom sans numéro): {item['name']}")
            continue
        url = f"https://drive.google.com/uc?export=download&id={item['id']}"
        planned.append((number, item["name"], slot, url, CAPTIONS[index % len(CAPTIONS)]))
        print(f"{item['name']} -> {slot.isoformat()}")

    if args.command == "plan":
        print("Mode test: aucune publication créée.")
        return

    for number, name, slot, url, caption in planned:
        result = api.create_tiktok(channel_id, slot.isoformat(), url, caption)
        if result.get("__typename") != "PostActionSuccess":
            raise RuntimeError(f"Buffer a refusé Video ({number}): {result}")
        state["used"].append(number)
        state["scheduled"].append({"video": number, "dueAt": slot.isoformat()})
        save_state(state)
        print(f"Programmé: {name}")


if __name__ == "__main__":
    main()
