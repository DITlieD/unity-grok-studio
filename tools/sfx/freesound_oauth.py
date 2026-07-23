#!/usr/bin/env python3
"""Freesound OAuth2 helper for original-quality downloads.

token auth (FREESOUND_TOKEN) only serves HQ previews; originals need OAuth2 Bearer.
credentials: ~/.config/sfx-forge/freesound.env  (FREESOUND_CLIENT_ID + FREESOUND_TOKEN,
where FREESOUND_TOKEN doubles as the client secret per Freesound's credential page).
token store: ~/.config/sfx-forge/freesound_oauth.json (chmod 600).

usage:
  freesound_oauth.py url                 print the authorize url for the owner to open
  freesound_oauth.py exchange CODE       exchange the pasted code for tokens
  freesound_oauth.py token               print a valid access token (auto-refresh)
  freesound_oauth.py whoami              verify the token against /apiv2/me/
"""
import json
import os
import stat
import sys
import time
import urllib.parse
import urllib.request

CONF_DIR = os.path.expanduser("~/.config/sfx-forge")
ENV_FILE = os.path.join(CONF_DIR, "freesound.env")
STORE = os.path.join(CONF_DIR, "freesound_oauth.json")
AUTHORIZE = "https://freesound.org/apiv2/oauth2/authorize/"
TOKEN_URL = "https://freesound.org/apiv2/oauth2/access_token/"
REFRESH_MARGIN_S = 300


def load_env():
    creds = {}
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                creds[k] = v
    cid = creds.get("FREESOUND_CLIENT_ID", "")
    secret = creds.get("FREESOUND_CLIENT_SECRET", creds.get("FREESOUND_TOKEN", ""))
    if not cid or not secret:
        sys.exit("missing FREESOUND_CLIENT_ID / secret in " + ENV_FILE)
    return cid, secret


def save_store(payload):
    payload["obtained_at"] = int(time.time())
    with open(STORE, "w") as f:
        json.dump(payload, f, indent=2)
    os.chmod(STORE, stat.S_IRUSR | stat.S_IWUSR)


def post_token(data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def cmd_url():
    cid, _ = load_env()
    q = urllib.parse.urlencode({"client_id": cid, "response_type": "code", "state": "sfxforge"})
    print(f"{AUTHORIZE}?{q}")


def cmd_exchange(code):
    cid, secret = load_env()
    payload = post_token({
        "client_id": cid,
        "client_secret": secret,
        "grant_type": "authorization_code",
        "code": code,
    })
    save_store(payload)
    print(f"stored; expires_in={payload.get('expires_in')}s scope={payload.get('scope')}")


def valid_token():
    cid, secret = load_env()
    if not os.path.exists(STORE):
        sys.exit("no token store; run: freesound_oauth.py url  then  exchange CODE")
    with open(STORE) as f:
        tok = json.load(f)
    age = time.time() - tok.get("obtained_at", 0)
    if age < tok.get("expires_in", 0) - REFRESH_MARGIN_S:
        return tok["access_token"]
    payload = post_token({
        "client_id": cid,
        "client_secret": secret,
        "grant_type": "refresh_token",
        "refresh_token": tok["refresh_token"],
    })
    save_store(payload)
    return payload["access_token"]


def cmd_whoami():
    tok = valid_token()
    req = urllib.request.Request(
        "https://freesound.org/apiv2/me/", headers={"Authorization": "Bearer " + tok}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        me = json.load(resp)
    print(f"authenticated as: {me.get('username')}")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "url":
        cmd_url()
    elif cmd == "exchange":
        if len(sys.argv) != 3:
            sys.exit("usage: freesound_oauth.py exchange CODE")
        cmd_exchange(sys.argv[2])
    elif cmd == "token":
        print(valid_token())
    elif cmd == "whoami":
        cmd_whoami()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
