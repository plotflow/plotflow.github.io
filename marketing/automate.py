#!/usr/bin/env python3
"""
PlotFlow Marketing Automation
Main automation script that generates content, schedules, and posts to Instagram.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
import argparse

# Local imports
from content_generator import ContentGenerator
from instagram_api import InstagramAPI
from scheduler import PostScheduler
from media_generator import MediaLibrary

SCRIPT_DIR = Path(__file__).parent


class MarketingAutomation:
    """Main automation controller."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.generator = ContentGenerator()
        self.api = InstagramAPI()
        self.scheduler = PostScheduler()
        self.media = MediaLibrary()

        print("🤖 PlotFlow Marketing Automation")
        print("=" * 60)
        if self.dry_run:
            print("⚠️  DRY RUN MODE - No actual posting will occur\n")

    def generate_content(self, days: int = 30):
        """Generate content for specified number of days."""
        posts_per_day = 3  # From settings
        total_posts = days * posts_per_day

        print(f"\n📝 Generating {total_posts} posts ({days} days × {posts_per_day}/day)...")
        batch = self.generator.generate_content_batch(count=total_posts)

        # Save batch
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"batch_{timestamp}.json"
        output_path = self.generator.save_content_batch(batch, filename)

        print(f"✓ Content saved to {output_path}")
        return batch

    def schedule_content(self, content_batch, start_date=None):
        """Schedule content batch for posting."""
        print(f"\n📅 Scheduling {len(content_batch)} posts...")

        if start_date is None:
            start_date = datetime.now(self.scheduler.timezone) + timedelta(days=1)

        scheduled = self.scheduler.generate_schedule(content_batch, start_date)
        self.scheduler.add_to_queue(scheduled)

        # Show schedule preview
        print(f"\n📋 Schedule Preview:")
        for i, post in enumerate(scheduled[:5]):
            sched_time = datetime.fromisoformat(post['scheduled_at'])
            print(f"   {i+1}. {sched_time.strftime('%b %d, %H:%M')} - {post['edition']} ({post['post_type']})")

        if len(scheduled) > 5:
            print(f"   ... and {len(scheduled) - 5} more")

        return scheduled

    def post_pending(self):
        """Post all pending content."""
        pending = self.scheduler.get_pending_posts()

        if not pending:
            print("\n📭 No posts due at this time")
            return

        print(f"\n📤 {len(pending)} posts ready to publish")

        if self.dry_run:
            print("\n🔍 DRY RUN - Would post:")
            for post in pending:
                key = post.get('edition_key', '')
                media_url = self.media.url_for(key, post['media_needed'])
                status = media_url if media_url else "⚠️  NO MEDIA (run media_generator build)"
                print(f"   - {post['edition']} ({post['post_type']}, {post['media_needed']})")
                print(f"       media: {status}")
            return

        # Post each pending item
        posted_count = 0
        failed_count = 0

        for post in pending:
            try:
                print(f"\n📢 Posting {post['edition']} ({post['media_needed']})...")

                # Select best caption variation (first one for now)
                caption = post['captions'][0]

                # Resolve the hosted media URL from the media manifest.
                key = post.get('edition_key', '')
                media_url = self.media.url_for(key, post['media_needed'])
                if not media_url:
                    raise RuntimeError(
                        f"No media for '{key}'. Run: python media_generator.py "
                        f"build --publish-dir ../assets/social (and commit it)."
                    )

                if post['media_needed'] == 'video':
                    post_id = self.api.post_video(media_url, caption)
                else:
                    post_id = self.api.post_image(media_url, caption)

                # Mark as posted
                self.scheduler.mark_posted(post['id'], post_id)
                posted_count += 1

                print(f"✓ Posted successfully: {post_id}")

            except Exception as e:
                print(f"❌ Failed to post {post['edition']}: {e}")
                self.scheduler.mark_failed(post['id'], str(e))
                failed_count += 1

        print(f"\n📊 Results: {posted_count} posted, {failed_count} failed")

    def show_status(self):
        """Display current automation status."""
        stats = self.scheduler.get_stats()

        print(f"\n📊 Current Status:")
        print(f"   Posts in queue: {stats['total_queued']}")
        print(f"   Posts published: {stats['total_posted']}")
        print(f"   Failed posts: {stats['total_failed']}")

        if stats['next_post']:
            next_time = datetime.fromisoformat(stats['next_post'])
            now = datetime.fromisoformat(stats['current_time'])
            time_until = next_time - now

            print(f"\n⏰ Next Scheduled Post:")
            print(f"   Edition: {stats['next_post_edition']}")
            print(f"   Time: {next_time.strftime('%Y-%m-%d %H:%M %Z')}")
            print(f"   In: {self._format_timedelta(time_until)}")

        # Check pending
        pending = self.scheduler.get_pending_posts()
        if pending:
            print(f"\n🔔 {len(pending)} posts are ready to publish now!")

    def _format_timedelta(self, td):
        """Format timedelta in human-readable format."""
        hours = td.total_seconds() // 3600
        minutes = (td.total_seconds() % 3600) // 60

        if hours >= 24:
            days = hours // 24
            hours = hours % 24
            return f"{int(days)} days, {int(hours)} hours"
        elif hours > 0:
            return f"{int(hours)} hours, {int(minutes)} minutes"
        else:
            return f"{int(minutes)} minutes"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='PlotFlow Instagram Marketing Automation')
    parser.add_argument('command', choices=['media', 'generate', 'schedule', 'post', 'status', 'full'],
                       help='Command to run')
    parser.add_argument('--days', type=int, default=30,
                       help='Number of days of content to generate (default: 30)')
    parser.add_argument('--publish-dir', default='../assets/social',
                       help='where media build copies files for public hosting (default: ../assets/social)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run without actually posting to Instagram')

    args = parser.parse_args()

    automation = MarketingAutomation(dry_run=args.dry_run)

    if args.command == 'media':
        # Render all edition media + manifest (build once, refresh when editions change)
        from media_generator import PlotRenderer
        renderer = PlotRenderer()
        publish = (SCRIPT_DIR / args.publish_dir).resolve()
        renderer.build_all(publish_dir=publish)

    elif args.command == 'generate':
        # Generate content only
        automation.generate_content(days=args.days)

    elif args.command == 'schedule':
        # Generate and schedule content
        batch = automation.generate_content(days=args.days)
        automation.schedule_content(batch)

    elif args.command == 'post':
        # Post pending content
        automation.post_pending()

    elif args.command == 'status':
        # Show status
        automation.show_status()

    elif args.command == 'full':
        # Full workflow: generate, schedule, and post pending
        batch = automation.generate_content(days=args.days)
        automation.schedule_content(batch)
        automation.post_pending()

    print("\n✨ Complete!")


if __name__ == '__main__':
    main()
