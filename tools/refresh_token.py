#!/usr/bin/env python3
"""
PLOTFLOW · Instagram token refresh
Exchanges the current long-lived token for a fresh 60-day one. Run on a
schedule (e.g. monthly) so the auto-poster never hits an expired token.

Reads from the environment:
    FB_APP_ID         Meta app id
    FB_APP_SECRET     Meta app secret
    IG_ACCESS_TOKEN   current long-lived token

Prints the new token to stdout (and to $GITHUB_OUTPUT as `token=` when run
in GitHub Actions). The refresh workflow then stores it back as a secret.
"""
import os, sys, json, urllib.request, urllib.parse, urllib.error

def main():
    app_id = os.environ.get("FB_APP_ID")
    app_secret = os.environ.get("FB_APP_SECRET")
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not (app_id and app_secret and token):
        sys.exit("Missing FB_APP_ID / FB_APP_SECRET / IG_ACCESS_TOKEN")

    version = os.environ.get("GRAPH_VERSION", "v21.0")
    q = urllib.parse.urlencode({
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": token,
    })
    url = f"https://graph.facebook.com/{version}/oauth/access_token?{q}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"Refresh failed {e.code}:\n{e.read().decode()}")

    new = data.get("access_token")
    if not new:
        sys.exit(f"No access_token in response: {data}")

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"token={new}\n")
    # also print masked confirmation
    print(f"Refreshed. New token length: {len(new)}, expires_in: {data.get('expires_in')}s")

if __name__ == "__main__":
    main()
