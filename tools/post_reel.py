#!/usr/bin/env python3
"""
PLOTFLOW · Instagram Reel auto-poster
Publishes a reel to an Instagram Business/Creator account via the Meta
Graph API Content Publishing flow:
    1. create a REELS media container (video_url + caption)
    2. poll the container until status_code == FINISHED
    3. publish the container

The video MUST already be live at a public HTTPS URL (we serve it from
GitHub Pages at https://plotflow.io/reels/<key>-<color>-reel.mp4).

Secrets are read from the environment — NEVER hard-code them:
    IG_USER_ID        Instagram Business account id (numeric)
    IG_ACCESS_TOKEN   long-lived access token (60-day, refreshable)
    GRAPH_VERSION     optional, defaults to v21.0

Usage:
    python3 tools/post_reel.py --key zaku
    python3 tools/post_reel.py --key zaku --color red --dry-run
    python3 tools/post_reel.py --auto        # pick this week's suit by rotation
"""
import os, sys, json, time, argparse, urllib.request, urllib.parse, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://plotflow.io"
GRAPH = "https://graph.facebook.com"

def load_editions():
    src = open(os.path.join(ROOT, "data", "editions.js")).read()
    src = src[src.index("{"):src.rindex("}") + 1]
    d = json.loads(src)
    return d["suits"], d.get("plotterOrder", list(d["suits"].keys()))

def load_captions():
    with open(os.path.join(ROOT, "tools", "captions.json")) as f:
        return json.load(f)

def week_index(n):
    # deterministic rotation: whole weeks since the unix epoch, mod n
    return int(time.time() // (7 * 86400)) % n

def api(method, path, params, version):
    url = f"{GRAPH}/{version}/{path}"
    data = urllib.parse.urlencode(params).encode()
    if method == "GET":
        url = url + "?" + data.decode()
        req = urllib.request.Request(url, method="GET")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise SystemExit(f"Graph API error {e.code} on {path}:\n{body}")

def url_is_live(url, tries=30, delay=10):
    """GitHub Pages can take ~1 min to deploy a new file — poll until 200."""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        print(f"  waiting for {url} to go live ({i+1}/{tries})…")
        time.sleep(delay)
    return False

def build_caption(caps, key):
    body = caps["captions"].get(key, "")
    return body + caps.get("_footer", "")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", help="edition key (e.g. zaku)")
    ap.add_argument("--color", default="red")
    ap.add_argument("--auto", action="store_true", help="pick this week's suit by rotation")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, don't call the API")
    ap.add_argument("--no-wait", action="store_true", help="skip waiting for the URL to go live")
    args = ap.parse_args()

    suits, order = load_editions()
    caps = load_captions()

    if args.auto and not args.key:
        args.key = order[week_index(len(order))]
    if not args.key:
        sys.exit("Provide --key <edition> or --auto")
    if args.key not in suits:
        sys.exit(f"Unknown edition '{args.key}'. Known: {', '.join(order)}")

    video_url = f"{SITE}/reels/{args.key}-{args.color}-reel.mp4"
    caption = build_caption(caps, args.key)
    version = os.environ.get("GRAPH_VERSION", "v21.0")

    print(f"Edition : {args.key} ({suits[args.key]['code']} {suits[args.key]['name']})")
    print(f"Video   : {video_url}")
    print(f"Caption :\n{caption}\n")

    if args.dry_run:
        print("[dry-run] not calling the Graph API.")
        return

    ig_user = os.environ.get("IG_USER_ID")
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not ig_user or not token:
        sys.exit("Missing IG_USER_ID / IG_ACCESS_TOKEN environment variables.")

    if not args.no_wait and not url_is_live(video_url):
        sys.exit(f"Video URL never became reachable: {video_url}")

    # 1. create container
    print("Creating media container…")
    container = api("POST", f"{ig_user}/media", {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": token,
    }, version)
    cid = container["id"]
    print(f"  container id: {cid}")

    # 2. poll until FINISHED (video transcode can take a minute or two)
    print("Waiting for Instagram to process the video…")
    for i in range(40):
        st = api("GET", cid, {"fields": "status_code,status", "access_token": token}, version)
        code = st.get("status_code")
        print(f"  status: {code} ({i+1}/40)")
        if code == "FINISHED":
            break
        if code == "ERROR":
            sys.exit(f"Processing failed: {st}")
        time.sleep(15)
    else:
        sys.exit("Timed out waiting for the container to finish processing.")

    # 3. publish
    print("Publishing…")
    pub = api("POST", f"{ig_user}/media_publish", {
        "creation_id": cid,
        "access_token": token,
    }, version)
    print(f"Published! Media id: {pub.get('id')}")

if __name__ == "__main__":
    main()
