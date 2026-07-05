# Instagram Reel automation

Auto-generates and posts a PLOTFLOW reel to Instagram on a schedule, with no
manual steps after the one-time setup below.

## How it works

```
GitHub Actions (weekly cron)
  → tools/gen_reel.py   renders reels/<key>-red-reel.mp4   (1080×1920 H.264)
  → commit to main      GitHub Pages serves it at plotflow.io/reels/<key>-red-reel.mp4
  → tools/post_reel.py  Meta Graph API: create container → poll → publish
                        caption pulled from tools/captions.json
```

Suit rotation is deterministic: `week_since_epoch % 6`, so each week posts the
next edition. Trigger manually anytime (and pick a specific suit) from the
Actions tab → **Post weekly reel to Instagram** → *Run workflow*.

## One-time setup

### 1. Account prerequisites
- Convert @plotflow to an Instagram **Business** or **Creator** account
  (Settings → Account type).
- Link it to a **Facebook Page** (Instagram Settings → linked accounts).

### 2. Create a Meta app
1. Go to https://developers.facebook.com/apps → **Create App** → type *Business*.
2. Add the **Instagram** product (Instagram Graph API).
3. Note the **App ID** and **App Secret** (Settings → Basic).

### 3. Get the IDs and a long-lived token
Use the **Graph API Explorer** (Tools menu) with your app selected:
1. Generate a user token with these permissions:
   `instagram_basic`, `instagram_content_publish`, `pages_show_list`,
   `business_management`.
2. Find your **Instagram Business account id**:
   `GET /me/accounts` → get the Page id → `GET /{page-id}?fields=instagram_business_account`.
   The returned `instagram_business_account.id` is your **IG_USER_ID**.
3. Exchange the short-lived token for a **long-lived** one (≈60 days):
   ```
   GET https://graph.facebook.com/v21.0/oauth/access_token
     ?grant_type=fb_exchange_token
     &client_id={APP_ID}
     &client_secret={APP_SECRET}
     &fb_exchange_token={SHORT_LIVED_TOKEN}
   ```
   The `access_token` in the response is your **IG_ACCESS_TOKEN**.

### 4. App Review
To publish to the public, submit `instagram_content_publish` for **App Review**.
While the app is in *Development* mode you can only publish to accounts that
have a role on the app — add @plotflow's user as a *Tester* (App Roles) to test
end-to-end before review is approved.

### 5. Add repo secrets
Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value | Used by |
|---|---|---|
| `IG_USER_ID` | Instagram Business account id | poster |
| `IG_ACCESS_TOKEN` | long-lived token | poster + refresh |
| `FB_APP_ID` | Meta app id | token refresh |
| `FB_APP_SECRET` | Meta app secret | token refresh |
| `GH_PAT` | fine-grained PAT, *Secrets: write* on this repo | token refresh |

`GH_PAT` is only needed so the monthly refresh can write the new token back.
Create it at GitHub → Settings → Developer settings → Fine-grained tokens,
scoped to this repo with **Secrets: Read and write**.

### 6. Token refresh (keeps it hands-off)
`.github/workflows/refresh-token.yml` runs on the 1st of each month, exchanges
the current token for a fresh 60-day one, and stores it back. Without this the
poster will start failing ~60 days after setup.

## Testing without posting
```bash
# Local dry run — builds the caption + URL, no API call:
python3 tools/post_reel.py --key zaku --dry-run
```
Or in Actions: *Run workflow* with **dry_run = true**.

## Editing captions
Edit `tools/captions.json`. Each edition has its own body; `_footer` (link +
hashtags) is appended to all of them. No code changes needed.

## Notes & limits
- Instagram allows **50 API-published posts per 24h** — far above our cadence.
- The video must be reachable at its public URL before publishing; the poster
  polls GitHub Pages until the file is live (Pages deploys take ~1 min).
- Secrets live only in GitHub Actions — never commit tokens to the repo.
