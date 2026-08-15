#!/usr/bin/env python3
"""
PLOTFLOW Instagram Content Generator
Generates engaging social media content from edition data with AI-powered variations.
"""

import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

try:
    import anthropic
except ImportError:
    anthropic = None  # AI captions disabled; template fallback still works

# Load settings
SCRIPT_DIR = Path(__file__).parent
with open(SCRIPT_DIR / 'config/settings.json') as f:
    SETTINGS = json.load(f)

# Edition data path (relative to repo root)
EDITIONS_PATH = SCRIPT_DIR.parent / 'data/editions.js'


class ContentGenerator:
    """Generates Instagram post content from PlotFlow editions."""

    def __init__(self):
        self.client = None
        if SETTINGS['ai']['enabled'] and anthropic is not None:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                self.client = anthropic.Anthropic(api_key=api_key)

    def load_editions(self) -> List[Dict[str, Any]]:
        """Load edition data from editions.js (window.PLOTFLOW = {...};)."""
        import re

        with open(EDITIONS_PATH) as f:
            content = f.read()

        # The file is `window.PLOTFLOW = { ... };` — valid JSON once the
        # assignment wrapper and trailing semicolon are stripped.
        m = re.search(r'window\.PLOTFLOW\s*=\s*', content)
        if not m:
            raise ValueError("Could not find window.PLOTFLOW assignment in editions.js")
        payload = content[m.end():].strip().rstrip(';').strip()

        data = json.loads(payload)
        suits = data.get('suits', {})
        order = data.get('shopOrder') or data.get('plotterOrder') or list(suits.keys())

        editions = []
        for key in order:
            suit = suits.get(key)
            if not suit:
                continue
            editions.append({
                "key": key,
                "code": suit.get('code', ''),
                "name": suit.get('name', ''),
                "name_jp": suit.get('jp', ''),
                "edition": suit.get('edition', ''),
                "price": self._parse_price(suit.get('price', '')),
                "description": suit.get('lore', ''),
            })

        return editions

    @staticmethod
    def _parse_price(price) -> str:
        """Normalize price to a display string like '$45'."""
        if isinstance(price, (int, float)):
            return f"${price:g}"
        s = str(price).strip()
        return s if s.startswith('$') else (f"${s}" if s else "")

    def generate_caption(self, edition: Dict[str, Any], post_type: str = "showcase") -> str:
        """Generate AI-powered caption for an edition."""
        if not self.client:
            return self._template_caption(edition, post_type)

        prompt = f"""Generate an engaging Instagram caption for a machine-drawn artwork with these details:

Edition: {edition['code']} — {edition['name']}
Japanese: {edition['name_jp']}
Edition run: {edition['edition']}
Price: {edition['price']}
Description: {edition['description']}

Post type: {post_type}

Style guidelines:
- {SETTINGS['ai']['style']}
- Tone: {SETTINGS['ai']['tone']}
- Keep it concise (2-4 sentences)
- Include both English and Japanese elements
- Emphasize マシンドロー — drawn by machine, stroke by stroke, never printed
- Mention it's machine-drawn by an AxiDraw plotter
- Make it compelling for art collectors and Gundam fans

Do not include hashtags in the caption (those are added separately).
"""

        try:
            response = self.client.messages.create(
                model=SETTINGS['ai']['model'],
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"AI generation failed: {e}, falling back to template")
            return self._template_caption(edition, post_type)

    def _template_caption(self, edition: Dict[str, Any], post_type: str) -> str:
        """Template-based caption generation as fallback."""
        templates = {
            "showcase": [
                f"{edition['code']} — {edition['name']}\n{edition['name_jp']}\n\n{edition['description']}\n\nDrawn by machine. Never printed. Limited edition.",
                f"マシンドロー — drawn by machine.\n\n{edition['name']} ({edition['code']}), traced stroke by stroke in ink by an AxiDraw plotter.\n\nEvery line, every detail — machine precision meets artistic vision.",
                f"{edition['name_jp']}\n{edition['name']} · {edition['code']}\n\n{edition['description']}\n\n{edition['price']} · {edition['edition']} · Plotted to order"
            ],
            "process": [
                f"Watch {edition['name']} come to life.\n\nEach piece starts as precise vector line work. The AxiDraw traces it line by line in technical pen on archival paper.\n\n{edition['code']} · {edition['name_jp']} · Machine drawn",
                f"The process: hours of precision.\n\n{edition['name']} plotted in real-time. Stroke by stroke, ink becomes form. Ink meets paper. Machine meets art.\n\nマシンドロー · {edition['code']}"
            ],
            "behind_scenes": [
                f"In the studio with {edition['code']}.\n\nStrathmore Bristol smooth, Staedtler Triplus 0.3mm fineliner, AxiDraw V3. Every piece drawn to order, inspected, signed, numbered.\n\n{edition['name']} · {edition['name_jp']}",
                f"Material matters.\n\nTechnical pen on archival paper. The AxiDraw follows the path with mechanical precision, but ink flow, temperature, and humidity mean no two plots are identical.\n\n{edition['code']} · Drawn by machine"
            ]
        }

        return random.choice(templates.get(post_type, templates['showcase']))

    def generate_hashtags(self, edition: Dict[str, Any], post_type: str) -> List[str]:
        """Generate relevant hashtags for the post."""
        tags = SETTINGS['content']['hashtags']['core'].copy()

        # Add type-specific tags
        if post_type == "showcase":
            tags.extend(SETTINGS['content']['hashtags']['art'])
            tags.extend(SETTINGS['content']['hashtags']['product'])
        elif post_type == "process":
            tags.extend(SETTINGS['content']['hashtags']['process'])
            tags.extend(SETTINGS['content']['hashtags']['art'][:3])
        else:  # behind_scenes
            tags.extend(SETTINGS['content']['hashtags']['process'])

        # Add edition-specific tags
        tags.append(f"#{edition['code'].replace('-', '')}")
        tags.append(f"#{edition['name'].replace(' ', '')}")

        # Limit to max hashtags and shuffle for variety
        random.shuffle(tags)
        return tags[:SETTINGS['content']['max_hashtags']]

    def create_post_content(self, edition: Dict[str, Any], post_type: str = "showcase") -> Dict[str, Any]:
        """Create complete post content package."""
        # Generate multiple caption variations
        captions = []
        for i in range(SETTINGS['content']['caption_variants']):
            caption = self.generate_caption(edition, post_type)
            hashtags = self.generate_hashtags(edition, post_type)
            full_caption = f"{caption}\n\n{' '.join(hashtags)}"
            captions.append(full_caption)

        return {
            "edition": edition['code'],
            "edition_key": edition.get('key', ''),
            "post_type": post_type,
            "captions": captions,
            "media_needed": self._get_media_type(post_type),
            "created_at": datetime.now().isoformat(),
            "metadata": {
                "name": edition['name'],
                "name_jp": edition['name_jp'],
                "price": edition['price'],
                "edition": edition['edition']
            }
        }

    def _get_media_type(self, post_type: str) -> str:
        """Determine media type needed for post.

        Process posts use the plotting video; everything else uses the
        showcase still. These map 1:1 to what media_generator produces.
        """
        return "video" if post_type == "process" else "image"

    def generate_content_batch(self, count: int = 30) -> List[Dict[str, Any]]:
        """Generate a batch of post content."""
        editions = self.load_editions()
        post_types = ["showcase", "process", "behind_scenes"]

        content_batch = []
        for i in range(count):
            edition = random.choice(editions)
            # Vary post types with weighted distribution
            post_type = random.choices(
                post_types,
                weights=[0.5, 0.3, 0.2],  # 50% showcase, 30% process, 20% BTS
                k=1
            )[0]

            content = self.create_post_content(edition, post_type)
            content_batch.append(content)

        return content_batch

    def save_content_batch(self, batch: List[Dict[str, Any]], filename: str = None):
        """Save generated content batch to file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"content_batch_{timestamp}.json"

        output_path = SCRIPT_DIR / 'content' / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(batch, f, indent=2)

        print(f"✓ Saved {len(batch)} posts to {output_path}")
        return output_path


def main():
    """Generate a batch of Instagram content."""
    print("🤖 PlotFlow Content Generator")
    print("=" * 50)

    generator = ContentGenerator()

    # Generate 30 days worth of content (3 posts per day = 90 posts)
    print("\nGenerating content batch...")
    batch = generator.generate_content_batch(count=90)

    # Save to file
    output_path = generator.save_content_batch(batch)

    # Print summary
    print(f"\n📊 Content Summary:")
    print(f"   Total posts: {len(batch)}")

    types = {}
    for post in batch:
        pt = post['post_type']
        types[pt] = types.get(pt, 0) + 1

    for post_type, count in types.items():
        print(f"   {post_type.title()}: {count}")

    print(f"\n📁 Output: {output_path}")
    print("\n✨ Content generation complete!")

    # Show sample
    print("\n📝 Sample post:")
    print("-" * 50)
    sample = batch[0]
    print(f"Edition: {sample['edition']}")
    print(f"Type: {sample['post_type']}")
    print(f"\nCaption variation 1:")
    print(sample['captions'][0])
    print("-" * 50)


if __name__ == '__main__':
    main()
