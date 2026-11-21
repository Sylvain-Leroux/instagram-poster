#!/usr/bin/env python3
"""Erneuert den langlebigen Instagram-Token (gueltig 60 Tage).

Gibt den neuen Token auf stdout aus; der Workflow speichert ihn als Secret.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

token = os.environ.get("IG_ACCESS_TOKEN")
if not token:
    sys.exit("IG_ACCESS_TOKEN fehlt")

query = urllib.parse.urlencode({"grant_type": "ig_refresh_token", "access_token": token})
try:
    with urllib.request.urlopen(
        f"https://graph.instagram.com/refresh_access_token?{query}", timeout=60
    ) as r:
        data = json.load(r)
except urllib.error.HTTPError as e:
    sys.exit(f"Erneuern fehlgeschlagen: HTTP {e.code}: {e.read().decode(errors='replace')}")

new = data["access_token"]
print(f"::add-mask::{new}")
print(f"Neuer Token gueltig fuer {int(data.get('expires_in', 0)) // 86400} Tage", file=sys.stderr)
with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as f:
    f.write(f"token={new}\n")
