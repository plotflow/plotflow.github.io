#!/usr/bin/env python3
"""
Instagram Graph API Integration
Handles posting images, videos, and carousels to Instagram Business accounts.
"""

import json
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Load settings
SCRIPT_DIR = Path(__file__).parent
with open(SCRIPT_DIR / 'config/settings.json') as f:
    SETTINGS = json.load(f)


class InstagramAPI:
    """Instagram Graph API wrapper for posting content."""

    def __init__(self, access_token: str = None, account_id: str = None):
        ig = SETTINGS['instagram']
        self.access_token = access_token or ig['access_token']
        self.account_id = account_id or ig['account_id']
        self.api_version = ig['api_version']
        # Two valid hosts depending on how you set up the app in Meta:
        #   graph.instagram.com  → "Instagram API with Instagram login"
        #                          (no Facebook Page needed: simplest for
        #                           publishing to your own @plotflow account)
        #   graph.facebook.com   → "Instagram API with Facebook login"
        #                          (requires an IG account linked to a FB Page)
        # Set instagram.graph_host in settings.json to pick. Defaults to the
        # Instagram-login host since @plotflow is a professional account.
        host = ig.get('graph_host', 'graph.instagram.com')
        self.base_url = f"https://{host}/{self.api_version}"

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request with error handling."""
        url = f"{self.base_url}/{endpoint}"
        kwargs.setdefault('params', {})['access_token'] = self.access_token

        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_data = response.json() if response.text else {}
            print(f"❌ API Error: {error_data}")
            raise

    def upload_media(self, media_url: str, caption: str, media_type: str = "IMAGE") -> str:
        """
        Upload media and create container.

        Args:
            media_url: Publicly accessible URL of the image/video
            caption: Post caption with hashtags
            media_type: "IMAGE" or "VIDEO"

        Returns:
            Container ID for publishing
        """
        endpoint = f"{self.account_id}/media"

        data = {
            "caption": caption,
        }

        if media_type == "VIDEO":
            data["media_type"] = "VIDEO"
            data["video_url"] = media_url
        else:
            data["image_url"] = media_url

        print(f"📤 Creating media container... ({media_type})")
        result = self._make_request('POST', endpoint, params=data)
        container_id = result.get('id')

        # For videos, wait for processing
        if media_type == "VIDEO":
            print(f"⏳ Processing video...")
            self._wait_for_video_processing(container_id)

        return container_id

    def _wait_for_video_processing(self, container_id: str, timeout: int = 300):
        """Wait for video to finish processing."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self._make_request('GET', container_id, params={'fields': 'status_code'})
            status_code = status.get('status_code')

            if status_code == 'FINISHED':
                print("✓ Video processing complete")
                return
            elif status_code == 'ERROR':
                raise Exception("Video processing failed")

            print(f"   Status: {status_code}...")
            time.sleep(10)

        raise TimeoutError("Video processing timeout")

    def create_carousel(self, media_urls: List[str], caption: str) -> str:
        """
        Create carousel post container.

        Args:
            media_urls: List of publicly accessible image URLs
            caption: Post caption

        Returns:
            Container ID for publishing
        """
        # First, create containers for each image
        children = []
        for i, url in enumerate(media_urls):
            print(f"📤 Uploading carousel item {i+1}/{len(media_urls)}...")
            item_data = {
                "image_url": url,
                "is_carousel_item": True
            }
            result = self._make_request('POST', f"{self.account_id}/media", params=item_data)
            children.append(result['id'])

        # Create carousel container
        print(f"📦 Creating carousel container...")
        carousel_data = {
            "caption": caption,
            "media_type": "CAROUSEL",
            "children": ','.join(children)
        }
        result = self._make_request('POST', f"{self.account_id}/media", params=carousel_data)
        return result['id']

    def publish_post(self, container_id: str) -> Dict[str, Any]:
        """
        Publish a media container to Instagram.

        Args:
            container_id: Media container ID from upload_media or create_carousel

        Returns:
            Published post data including post ID
        """
        print(f"📢 Publishing to Instagram...")
        endpoint = f"{self.account_id}/media_publish"
        result = self._make_request('POST', endpoint, params={'creation_id': container_id})

        post_id = result.get('id')
        print(f"✓ Published! Post ID: {post_id}")
        return result

    def post_image(self, image_url: str, caption: str) -> str:
        """Post single image (convenience method)."""
        container_id = self.upload_media(image_url, caption, "IMAGE")
        result = self.publish_post(container_id)
        return result['id']

    def post_video(self, video_url: str, caption: str) -> str:
        """Post video (convenience method)."""
        container_id = self.upload_media(video_url, caption, "VIDEO")
        result = self.publish_post(container_id)
        return result['id']

    def post_carousel(self, image_urls: List[str], caption: str) -> str:
        """Post carousel (convenience method)."""
        container_id = self.create_carousel(image_urls, caption)
        result = self.publish_post(container_id)
        return result['id']

    def get_account_info(self) -> Dict[str, Any]:
        """Get Instagram account information."""
        endpoint = self.account_id
        return self._make_request('GET', endpoint, params={
            'fields': 'name,username,profile_picture_url,followers_count,media_count'
        })

    def test_connection(self) -> bool:
        """Test API connection and credentials."""
        try:
            info = self.get_account_info()
            print(f"✓ Connected to Instagram account: @{info.get('username')}")
            print(f"  Followers: {info.get('followers_count', 'N/A')}")
            print(f"  Posts: {info.get('media_count', 'N/A')}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False


def main():
    """Test Instagram API connection."""
    print("🔌 Testing Instagram API Connection")
    print("=" * 50)

    api = InstagramAPI()

    if api.access_token == "YOUR_INSTAGRAM_ACCESS_TOKEN":
        print("\n⚠️  No access token configured!")
        print("\nTo set up Instagram API:")
        print("1. Create a Facebook App at developers.facebook.com")
        print("2. Add Instagram Graph API product")
        print("3. Connect your Instagram Business account")
        print("4. Generate an access token")
        print("5. Update marketing/config/settings.json with your credentials")
        print("\nSee: https://developers.facebook.com/docs/instagram-api/getting-started")
        return

    # Test connection
    api.test_connection()


if __name__ == '__main__':
    main()
