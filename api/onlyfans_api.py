"""OnlyFans API Client

Handles all OnlyFans API interactions including:
- User/creator account information
- Timeline posts
- Single posts
- Messages (future)
- Collections/Vault (future)

Completely separate from Fansly API.
"""

import requests
import time
from typing import Optional, Dict, List
from api.onlyfans_auth import OnlyFansAuth


class OnlyFansApi:
    """OnlyFans API client with authentication"""

    # OnlyFans API base URL
    BASE_URL = "https://onlyfans.com/api2/v2"

    def __init__(self, sess: str, auth_id: str, auth_uid: Optional[str],
                 user_agent: str, x_bc: str):
        """
        Initialize OnlyFans API client

        Args:
            sess: Session cookie
            auth_id: Auth ID
            auth_uid: Auth UID (if 2FA enabled)
            user_agent: Browser user agent
            x_bc: X-BC token
        """
        self.sess = sess
        self.auth_id = auth_id
        self.auth_uid = auth_uid
        self.user_agent = user_agent
        self.x_bc = x_bc

        self.session = requests.Session()
        self.auth = OnlyFansAuth(sess, auth_id, auth_uid, user_agent, x_bc)

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make authenticated API request

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL or path (will prepend BASE_URL if needed)
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            requests.HTTPError: If request fails
        """
        # Prepend base URL if not already included
        if not url.startswith('http'):
            url = f"{self.BASE_URL}{url}"

        # If params provided, add them to URL NOW (before signature)
        # This ensures the signature includes the query string
        if 'params' in kwargs:
            from urllib.parse import urlencode, urlparse, urlunparse
            params = kwargs.pop('params')
            query_string = urlencode(params)
            
            # Check if URL already has query parameters
            parsed = urlparse(url)
            if parsed.query:
                # URL already has query params, append with &
                url = f"{url}&{query_string}"
            else:
                # No existing query params, use ?
                url = f"{url}?{query_string}"

        # Get auth headers and cookies
        headers = self.auth.get_headers(url)
        cookies = self.auth.get_cookies()

        # Merge with any provided headers/cookies
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))
        if 'cookies' in kwargs:
            cookies.update(kwargs.pop('cookies'))

        # Make request
        response = self.session.request(
            method=method,
            url=url,
            headers=headers,
            cookies=cookies,
            **kwargs
        )

        # Raise for HTTP errors
        response.raise_for_status()

        return response

    def test_auth(self) -> bool:
        """
        Test authentication by calling /users/me endpoint

        Returns:
            True if authentication successful

        Raises:
            requests.HTTPError: If authentication fails
        """
        response = self._make_request('GET', '/users/me')
        return response.status_code == 200

    def get_my_info(self) -> Dict:
        """
        Get current user's account information

        Returns:
            Dict with user account data
        """
        response = self._make_request('GET', '/users/me')
        return response.json()

    def get_user_by_username(self, username: str) -> Dict:
        """
        Get user information by username

        Args:
            username: Creator's username

        Returns:
            Dict with user data including ID, name, avatar, etc.
        """
        response = self._make_request('GET', f'/users/{username}')
        return response.json()

    def get_user_by_id(self, user_id: str) -> Dict:
        """
        Get user information by ID

        Args:
            user_id: Creator's user ID

        Returns:
            Dict with user data
        """
        response = self._make_request('GET', f'/users/{user_id}')
        return response.json()

    def get_timeline(self, user_id: str, limit: int = 100,
                     before_publish_time: Optional[str] = None) -> Dict:
        """
        Get timeline posts for a user

        Args:
            user_id: Creator's user ID
            limit: Number of posts to fetch (default: 100)
            before_publish_time: Fetch posts before this timestamp (pagination)

        Returns:
            Dict with:
                - list: Array of post objects
                - hasMore: Boolean indicating more posts available
                - nextCursor: Cursor for next page (if hasMore is True)
        """
        # OnlyFans API requires these specific query parameters
        # Based on OF-Scraper implementation
        params = {
            'limit': limit,
            'order': 'publish_date_desc',  # Newest posts first
            'skip_users': 'all',
            'skip_users_dups': '1',
            'pinned': '0',
            'format': 'infinite',
        }

        if before_publish_time:
            params['beforePublishTime'] = before_publish_time

        response = self._make_request('GET', f'/users/{user_id}/posts', params=params)
        return response.json()

    def get_post(self, post_id: str) -> Dict:
        """
        Get single post by ID

        Args:
            post_id: Post ID

        Returns:
            Dict with post data
        """
        response = self._make_request('GET', f'/posts/{post_id}')
        return response.json()

    def get_user_media(self, user_id: str, limit: int = 100,
                       before_publish_time: Optional[str] = None) -> Dict:
        """
        Get media from user's media tab

        Args:
            user_id: Creator's user ID
            limit: Number of media items to fetch
            before_publish_time: Pagination cursor

        Returns:
            Dict with media items
        """
        params = {
            'limit': limit,
        }

        if before_publish_time:
            params['beforePublishTime'] = before_publish_time

        response = self._make_request('GET', f'/users/{user_id}/posts/photos', params=params)
        return response.json()

    def get_subscriptions(self, limit: int = 100, offset: int = 0) -> Dict:
        """
        Get current user's subscriptions

        Args:
            limit: Number of subscriptions to fetch
            offset: Offset for pagination

        Returns:
            Dict with subscription data
        """
        params = {
            'limit': limit,
            'offset': offset,
        }

        response = self._make_request('GET', '/subscriptions/subscribes', params=params)
        return response.json()

    # Future: Messages API
    def get_chats(self) -> Dict:
        """Get list of chats (messages) - TODO: Implement"""
        raise NotImplementedError("Messages support coming in future update")

    def get_messages(self, chat_id: str) -> Dict:
        """Get messages from a chat - TODO: Implement"""
        raise NotImplementedError("Messages support coming in future update")

    # Future: Collections/Vault API
    def get_vault_lists(self) -> Dict:
        """Get vault/collection lists - TODO: Implement"""
        raise NotImplementedError("Collections support coming in future update")

    def get_vault_media(self, list_id: str) -> Dict:
        """Get media from vault list - TODO: Implement"""
        raise NotImplementedError("Collections support coming in future update")
