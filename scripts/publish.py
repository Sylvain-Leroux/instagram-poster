#!/usr/bin/env python3
"""Veroeffentlicht faellige Posts aus queue/ auf Instagram.

Jeder Post ist ein Ordner in queue/ mit:
  post.json   {"publish_at": "2026-11-24T18:30:00+01:00", "caption": "..."}
  01.jpg, 02.jpg, ...   (1 bis 10 Bilder, JPEG, max. 8 MB, am besten 1080x1350)

Erfolgreich gepostete Ordner wandern nach posted/, fehlgeschlagene nach failed/.
Nur Python-Standardbibliothek, keine Installation noetig.
"""
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_VERSION = os.environ.get("IG_API_VERSION", "v25.0")
BASE = f"https://graph.instagram.com/{API_VERSION}"
ROOT = Path(__file__).resolve().parent.parent
QUEUE, POSTED, FAILED = ROOT / "queue", ROOT / "posted", ROOT / "failed"
MAX_PER_RUN = 3
MAX_IMAGE_BYTES = 8 * 1024 * 1024


class IGError(Exception):
    pass


def api(method, path, params, token):
    params = dict(params, access_token=token)
    data = urllib.parse.urlencode(params).encode()
    url = f"{BASE}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise IGError(f"{method} {path} -> HTTP {e.code}: {body}") from None


def wait_finished(container_id, token, tries=30, pause=5):
    for _ in range(tries):
        status = api("GET", container_id, {"fields": "status_code,status"}, token)
        code = status.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise IGError(f"Container {container_id}: {status}")
        time.sleep(pause)
    raise IGError(f"Container {container_id} wurde nicht fertig")


def image_url(repo, branch, folder, name):
    path = urllib.parse.quote(f"queue/{folder}/{name}")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"


def validate(folder):
    meta_file = folder / "post.json"
    if not meta_file.exists():
        raise IGError("post.json fehlt")
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    caption = meta.get("caption", "")
    if len(caption) > 2200:
        raise IGError(f"Caption zu lang ({len(caption)} > 2200 Zeichen)")
    if caption.count("#") > 30:
        raise IGError("Mehr als 30 Hashtags")
    images = meta.get("images") or sorted(
        p.name for p in folder.iterdir() if p.suffix.lower() in (".jpg", ".jpeg")
    )
    if not 1 <= len(images) <= 10:
        raise IGError(f"{len(images)} Bilder, erlaubt sind 1 bis 10")
    for name in images:
        p = folder / name
        if not p.exists():
            raise IGError(f"Bild fehlt: {name}")
        if p.stat().st_size > MAX_IMAGE_BYTES:
            raise IGError(f"Bild zu gross (> 8 MB): {name}")
    publish_at = datetime.fromisoformat(meta["publish_at"])
    if publish_at.tzinfo is None:
        raise IGError("publish_at braucht eine Zeitzone, z. B. +01:00")
    return meta, caption, images, publish_at


def publish(folder, caption, images, token, user_id, repo, branch):
    urls = [image_url(repo, branch, folder.name, n) for n in images]
    if len(urls) == 1:
        container = api("POST", f"{user_id}/media",
                        {"image_url": urls[0], "caption": caption}, token)["id"]
    else:
        children = []
        for u in urls:
            cid = api("POST", f"{user_id}/media",
                      {"image_url": u, "is_carousel_item": "true"}, token)["id"]
            children.append(cid)
        for cid in children:
            wait_finished(cid, token)
        container = api("POST", f"{user_id}/media", {
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "caption": caption,
        }, token)["id"]
    wait_finished(container, token)
    return api("POST", f"{user_id}/media_publish",
               {"creation_id": container}, token)["id"]


def move(folder, target_root, info):
    target_root.mkdir(exist_ok=True)
    (folder / "result.json").write_text(json.dumps(info, indent=2, ensure_ascii=False),
                                        encoding="utf-8")
    shutil.move(str(folder), str(target_root / folder.name))


def main():
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
    token = os.environ.get("IG_ACCESS_TOKEN", "")
    user_id = os.environ.get("IG_USER_ID", "me")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    if not dry_run and not token:
        sys.exit("IG_ACCESS_TOKEN fehlt (GitHub Secret anlegen)")

    now = datetime.now(timezone.utc)
    folders = sorted(p for p in QUEUE.glob("*") if p.is_dir()) if QUEUE.exists() else []
    done, failed = 0, 0
    for folder in folders:
        if done >= MAX_PER_RUN:
            break
        try:
            meta, caption, images, publish_at = validate(folder)
        except Exception as e:  # noqa: BLE001
            print(f"[FEHLER] {folder.name}: {e}")
            if not dry_run:
                move(folder, FAILED, {"error": str(e), "at": now.isoformat()})
            failed += 1
            continue
        if publish_at > now:
            print(f"[WARTET] {folder.name} bis {publish_at.isoformat()}")
            continue
        if dry_run:
            print(f"[TEST] {folder.name}: {len(images)} Bilder, waere jetzt faellig")
            for n in images:
                print("   ", image_url(repo, branch, folder.name, n))
            continue
        try:
            media_id = publish(folder, caption, images, token, user_id, repo, branch)
            print(f"[GEPOSTET] {folder.name} -> Media-ID {media_id}")
            move(folder, POSTED, {"media_id": media_id,
                                  "posted_at": datetime.now(timezone.utc).isoformat()})
            done += 1
        except Exception as e:  # noqa: BLE001
            print(f"[FEHLER] {folder.name}: {e}")
            move(folder, FAILED, {"error": str(e), "at": now.isoformat()})
            failed += 1
    print(f"Fertig: {done} gepostet, {failed} fehlgeschlagen")
    if failed:
        sys.exit(1)  # GitHub schickt dann eine Fehler-Mail


if __name__ == "__main__":
    main()
