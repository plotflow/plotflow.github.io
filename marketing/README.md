# PlotFlow Marketing Automation

Automated Instagram content generation and posting system for PlotFlow artwork.

## 🎯 Features

- **AI-Powered Content Generation**: Creates engaging captions with Claude AI
- **Multi-Variant Captions**: Generates 3 different caption options per post
- **Smart Scheduling**: Distributes posts across optimal times
- **Full Instagram API Integration**: Automated posting of images, videos, and carousels
- **Post Type Variety**: Showcases, process videos, and behind-the-scenes content
- **Bilingual**: English and Japanese (一筆書き) content
- **Queue Management**: Track posted, pending, and failed posts

## 📋 Prerequisites

1. **Instagram Business Account**
2. **Facebook Developer Account**
3. **Instagram Access Token** (see setup below)
4. **Anthropic API Key** (for AI content generation)

## 🚀 Setup

### 1. Install Dependencies

```bash
cd marketing
pip install -r requirements.txt
```

### 2. Create Your Settings File

The real `settings.json` is gitignored (it holds your tokens). Copy the template:

```bash
cp config/settings.example.json config/settings.json
```

Then fill in your credentials in `config/settings.json`.

### 3. Configure Instagram API

1. Go to [Facebook for Developers](https://developers.facebook.com/)
2. Create a new app
3. Add **Instagram Graph API** product
4. Connect your Instagram Business account
5. Generate a long-lived access token
6. Update `config/settings.json`:

```json
{
  "instagram": {
    "access_token": "YOUR_ACCESS_TOKEN_HERE",
    "account_id": "YOUR_INSTAGRAM_BUSINESS_ACCOUNT_ID"
  }
}
```

**Getting your account ID:**
```bash
curl -X GET "https://graph.facebook.com/v21.0/me/accounts?access_token=YOUR_TOKEN"
```

### 4. Set Anthropic API Key

```bash
export ANTHROPIC_API_KEY="your_api_key_here"
```

Or add to `.env` file:
```
ANTHROPIC_API_KEY=sk-ant-...
```

### 5. Test Connection

```bash
python instagram_api.py  # Test Instagram API
python content_generator.py  # Generate sample content
```

## 🎬 Media Generation

Instagram needs publicly-hosted media. The media generator renders each
edition's continuous-line path into two Instagram-ready assets — no browser,
no system ffmpeg (a static binary ships with `imageio-ffmpeg`):

- **`{key}_process.mp4`** — 1080×1080 H.264 video of the suit drawn line-by-line
  in red ink on Bristol paper, with the moving pen head and bed label. Used for
  *process* posts.
- **`{key}_showcase.png`** — 1080×1350 still of the finished plot, composed as a
  feed image with code / edition / name / 日本語 / price. Used for everything else.

### Build the media + manifest

```bash
python media_generator.py build --publish-dir ../assets/social
```

This renders all six editions, writes `media/generated/manifest.json` (the
map the poster reads), and copies the files into `assets/social/`. Commit that
folder so GitHub Pages serves them at `https://plotflow.io/assets/social/…`,
which is what the Instagram API fetches. The public URL base is set in
`config/settings.json` under `site`.

You only need to rebuild when editions change. Other handy forms:

```bash
python media_generator.py list                    # list editions
python media_generator.py still --key zaku         # one still
python media_generator.py video --key zaku --duration 20
python automate.py media                           # build all + publish (via automate)
```

## 📤 Manual posting (no Meta API)

If the Meta API is unavailable — a disabled/appealed Facebook account, no
approved app, or you just want to post by hand — use the exporter. It turns the
editorial card library into ready-to-post packs plus a browser review board, so
you publish through the Instagram app in seconds. No API, no approval, no
account dependency.

```bash
python tools/gen_posts.py    # (run from repo root) build the 26 cards
python automate.py export    # write packs + grouped review board
```

`export` bundles the card library (`assets/posts/`): the 5 styles per suit
(process, lore, spec, drop) plus the two brand cards, each paired with its
canon caption from `tools/captions.json`. It creates `exports/<timestamp>/`:

- one folder per card with the **card image** + **caption.txt**
- **index.html** — a review board grouped by suit, each card with a **Copy
  caption** button

(Use `python automate.py export` → falls back to `--queue` for the older
still+video scheduler set if you ever need it: `python exporter.py --queue`.)

Open `index.html`, and for each card: click *Copy caption*, save the image, and
post it in the Instagram app. Fastest on your phone — AirDrop/sync the folder,
or open the board on mobile.

## 📖 Usage (Meta API path)

### Generate Content (30 days worth)

```bash
python automate.py generate --days 30
```

This creates 90 posts (3 per day) with AI-generated captions.

### Generate & Schedule

```bash
python automate.py schedule --days 30
```

Creates content and adds to posting queue with optimal timing.

### Post Pending Content

```bash
python automate.py post
```

Posts everything due now. Run this via cron for full automation.

### Check Status

```bash
python automate.py status
```

Shows queue stats and next scheduled post.

### Full Workflow

```bash
python automate.py full --days 30
```

Generate, schedule, and post pending in one command.

### Dry Run Mode

Test without actually posting:

```bash
python automate.py post --dry-run
```

## 🤖 Automation (Cron)

Add to crontab for automatic posting:

```bash
# Post pending content every hour
0 * * * * cd /path/to/plotflow.github.io/marketing && python automate.py post >> logs/cron.log 2>&1

# Generate new content weekly
0 9 * * 1 cd /path/to/plotflow.github.io/marketing && python automate.py schedule --days 7 >> logs/cron.log 2>&1
```

## 📁 File Structure

```
marketing/
├── automate.py           # Main automation script
├── content_generator.py  # AI content generation
├── instagram_api.py      # Instagram Graph API wrapper
├── scheduler.py          # Post scheduling logic
├── requirements.txt      # Python dependencies
├── config/
│   └── settings.json    # Configuration (API keys, schedule, hashtags)
├── content/
│   ├── batch_*.json     # Generated content batches
│   ├── post_queue.json  # Scheduled posts queue
│   └── post_history.json # Posted content history
├── media/
│   └── generated/       # Generated images/videos
└── logs/
    └── cron.log         # Automation logs
```

## 🎨 Content Types

**Showcase (50%)**: Finished artwork photos
- Highlights the completed piece
- Technical details and pricing
- High-quality product shots

**Process (30%)**: Timelapse videos
- Shows the plotter in action
- One continuous line being drawn
- Mesmerizing machine art

**Behind-the-Scenes (20%)**: Studio content
- Materials and tools
- Setup shots
- Process insights

## 🎯 Posting Strategy

- **3 posts per day** at optimal times (9am, 1pm, 5pm, 8pm)
- **Minimum 3 hours** between posts
- **7 days a week** coverage
- **Smart hashtags**: 20 relevant tags per post
- **Bilingual content**: English + Japanese (一筆書き)

## 🔧 Customization

### Adjust Posting Schedule

Edit `config/settings.json`:

```json
{
  "posting": {
    "schedule": {
      "times": ["09:00", "13:00", "17:00", "20:00"],
      "timezone": "America/New_York",
      "days": ["monday", "tuesday", ...]
    },
    "frequency": {
      "daily_limit": 3,
      "min_hours_between": 3
    }
  }
}
```

### Customize Hashtags

```json
{
  "content": {
    "hashtags": {
      "core": ["#plotflow", "一筆書き", "#penplotter"],
      "art": ["#gundam", "#mobilesuit", ...],
      "process": ["#plotter", "#axidraw", ...],
      "product": ["#limitedEdition", ...]
    }
  }
}
```

### AI Generation Style

```json
{
  "ai": {
    "tone": "artistic, technical, minimalist",
    "style": "Blend Japanese aesthetics with technical precision..."
  }
}
```

## 📊 Monitoring

Check `content/post_history.json` for analytics:
- Posted vs. failed rate
- Best performing post types
- Engagement patterns (requires manual tracking)

## ⚠️ Important Notes

1. **Media URLs**: Posts require publicly accessible image/video URLs
2. **Rate Limits**: Instagram has posting limits (check API docs)
3. **Content Review**: Always review AI-generated content before posting
4. **Backup Queue**: Keep backups of `post_queue.json`
5. **Token Expiry**: Instagram tokens expire; renew regularly

## 🆘 Troubleshooting

**"Access token invalid"**
- Regenerate token in Facebook Developer Console
- Ensure Instagram account is Business type
- Check account_id is correct

**"Media not found"**
- Media URLs must be publicly accessible
- Use HTTPS, not HTTP
- Test URL in browser first

**"No posts generated"**
- Check ANTHROPIC_API_KEY is set
- Verify `data/editions.js` exists
- Run content_generator.py standalone

## 📚 Resources

- [Instagram Graph API Docs](https://developers.facebook.com/docs/instagram-api)
- [Instagram Content Publishing](https://developers.facebook.com/docs/instagram-api/guides/content-publishing)
- [Access Token Guide](https://developers.facebook.com/docs/instagram-basic-display-api/overview#instagram-user-access-tokens)

---

**Built for PlotFlow** · 一筆書き · Machine-drawn art automation
