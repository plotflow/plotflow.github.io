#!/usr/bin/env python3
"""
Post Scheduler
Manages posting queue and timing for Instagram automation.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import pytz

# Load settings
SCRIPT_DIR = Path(__file__).parent
with open(SCRIPT_DIR / 'config/settings.json') as f:
    SETTINGS = json.load(f)


class PostScheduler:
    """Manages scheduling and queuing of Instagram posts."""

    def __init__(self):
        self.timezone = pytz.timezone(SETTINGS['posting']['schedule']['timezone'])
        self.queue_file = SCRIPT_DIR / 'content/post_queue.json'
        self.history_file = SCRIPT_DIR / 'content/post_history.json'
        self.queue = self._load_queue()
        self.history = self._load_history()

    def _load_queue(self) -> List[Dict[str, Any]]:
        """Load posting queue from file."""
        if self.queue_file.exists():
            with open(self.queue_file) as f:
                return json.load(f)
        return []

    def _save_queue(self):
        """Save posting queue to file."""
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.queue_file, 'w') as f:
            json.dump(self.queue, f, indent=2)

    def _load_history(self) -> List[Dict[str, Any]]:
        """Load posting history."""
        if self.history_file.exists():
            with open(self.history_file) as f:
                return json.load(f)
        return []

    def _save_history(self):
        """Save posting history."""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)

    def generate_schedule(self, content_batch: List[Dict[str, Any]], start_date: datetime = None) -> List[Dict[str, Any]]:
        """
        Generate posting schedule from content batch.

        Args:
            content_batch: List of generated post content
            start_date: When to start scheduling (default: tomorrow)

        Returns:
            Scheduled posts with dates/times
        """
        if start_date is None:
            start_date = datetime.now(self.timezone) + timedelta(days=1)
            start_date = start_date.replace(hour=9, minute=0, second=0, microsecond=0)

        schedule_settings = SETTINGS['posting']['schedule']
        post_times = schedule_settings['times']
        active_days = [d.lower() for d in schedule_settings['days']]
        daily_limit = SETTINGS['posting']['frequency']['daily_limit']

        scheduled_posts = []
        current_date = start_date
        posts_today = 0

        for post_content in content_batch:
            # Check if we've hit daily limit
            if posts_today >= daily_limit:
                current_date += timedelta(days=1)
                posts_today = 0

            # Skip if day is not active
            while current_date.strftime('%A').lower() not in active_days:
                current_date += timedelta(days=1)
                posts_today = 0

            # Pick a random time from configured times
            time_str = random.choice(post_times)
            hour, minute = map(int, time_str.split(':'))
            scheduled_time = current_date.replace(hour=hour, minute=minute)

            # Add some randomness (±15 minutes) to feel more natural
            random_offset = random.randint(-15, 15)
            scheduled_time += timedelta(minutes=random_offset)

            scheduled_post = {
                **post_content,
                "scheduled_at": scheduled_time.isoformat(),
                "status": "queued",
                "id": f"{post_content['edition']}_{scheduled_time.strftime('%Y%m%d_%H%M')}"
            }

            scheduled_posts.append(scheduled_post)
            posts_today += 1

        return scheduled_posts

    def add_to_queue(self, posts: List[Dict[str, Any]]):
        """Add posts to the posting queue."""
        self.queue.extend(posts)
        self.queue.sort(key=lambda x: x['scheduled_at'])
        self._save_queue()
        print(f"✓ Added {len(posts)} posts to queue")

    def get_pending_posts(self, until: datetime = None) -> List[Dict[str, Any]]:
        """Get posts that are due to be posted."""
        if until is None:
            until = datetime.now(self.timezone)

        until_iso = until.isoformat()

        pending = [
            post for post in self.queue
            if post['status'] == 'queued' and post['scheduled_at'] <= until_iso
        ]

        return pending

    def mark_posted(self, post_id: str, instagram_post_id: str = None):
        """Mark a post as published."""
        for post in self.queue:
            if post['id'] == post_id:
                post['status'] = 'posted'
                post['posted_at'] = datetime.now(self.timezone).isoformat()
                if instagram_post_id:
                    post['instagram_id'] = instagram_post_id

                # Move to history
                self.history.append(post)
                self.queue.remove(post)

                self._save_queue()
                self._save_history()
                break

    def mark_failed(self, post_id: str, error: str):
        """Mark a post as failed."""
        for post in self.queue:
            if post['id'] == post_id:
                post['status'] = 'failed'
                post['error'] = error
                post['failed_at'] = datetime.now(self.timezone).isoformat()
                self._save_queue()
                break

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduling statistics."""
        now = datetime.now(self.timezone)

        queued = [p for p in self.queue if p['status'] == 'queued']
        failed = [p for p in self.queue if p['status'] == 'failed']

        # Find next post time
        next_post = None
        if queued:
            next_post = min(queued, key=lambda x: x['scheduled_at'])

        return {
            "total_queued": len(queued),
            "total_posted": len(self.history),
            "total_failed": len(failed),
            "next_post": next_post['scheduled_at'] if next_post else None,
            "next_post_edition": next_post['edition'] if next_post else None,
            "current_time": now.isoformat()
        }


def main():
    """Example usage of scheduler."""
    print("📅 Post Scheduler")
    print("=" * 50)

    scheduler = PostScheduler()

    # Show current stats
    stats = scheduler.get_stats()
    print(f"\n📊 Current Status:")
    print(f"   Queued: {stats['total_queued']}")
    print(f"   Posted: {stats['total_posted']}")
    print(f"   Failed: {stats['total_failed']}")

    if stats['next_post']:
        next_time = datetime.fromisoformat(stats['next_post'])
        print(f"\n⏰ Next Post:")
        print(f"   Edition: {stats['next_post_edition']}")
        print(f"   Time: {next_time.strftime('%Y-%m-%d %H:%M %Z')}")

    # Check for pending posts
    pending = scheduler.get_pending_posts()
    if pending:
        print(f"\n🔔 {len(pending)} posts ready to publish!")
        for post in pending[:3]:  # Show first 3
            print(f"   - {post['edition']} ({post['post_type']})")


if __name__ == '__main__':
    main()
