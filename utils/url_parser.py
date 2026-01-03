"""URL Parsing and Platform Detection Utilities

Shared utilities for detecting platform from URLs and extracting post IDs
for both Fansly and OnlyFans.
"""

import re
from enum import Enum
from typing import Optional, Tuple


class Platform(Enum):
    """Supported platforms"""
    FANSLY = "fansly"
    ONLYFANS = "onlyfans"
    UNKNOWN = "unknown"


# URL patterns
FANSLY_POST_PATTERN = re.compile(
    r'https?://(?:www\.)?fansly\.com/post/(\d+)',
    re.IGNORECASE
)

ONLYFANS_POST_PATTERN = re.compile(
    r'https?://(?:www\.)?onlyfans\.com/(\d+)/(\w+)',
    re.IGNORECASE
)


def detect_platform_from_url(url: str) -> Tuple[Platform, Optional[str], Optional[str]]:
    """
    Detect platform and extract post ID from URL.

    Args:
        url: Post URL or raw post ID

    Returns:
        Tuple of (platform, post_id, creator_username)
        - For Fansly: (FANSLY, post_id, None)
        - For OnlyFans: (ONLYFANS, post_id, username)
        - For raw ID/unknown: (UNKNOWN, None, None)
    """
    url = url.strip()

    # Try Fansly pattern
    fansly_match = FANSLY_POST_PATTERN.match(url)
    if fansly_match:
        return (Platform.FANSLY, fansly_match.group(1), None)

    # Try OnlyFans pattern
    of_match = ONLYFANS_POST_PATTERN.match(url)
    if of_match:
        return (Platform.ONLYFANS, of_match.group(1), of_match.group(2))

    return (Platform.UNKNOWN, None, None)


def is_valid_onlyfans_post_id(post_id: str) -> bool:
    """
    Validate OnlyFans post ID format.

    OnlyFans post IDs are numeric and typically 6+ digits.

    Args:
        post_id: The post ID string to validate

    Returns:
        True if valid, False otherwise
    """
    if not post_id:
        return False
    return post_id.isdigit() and len(post_id) >= 6


def get_post_id_from_onlyfans_url(url: str) -> Optional[str]:
    """
    Extract post ID from OnlyFans URL.

    Args:
        url: OnlyFans post URL

    Returns:
        Post ID string or None if not found
    """
    match = ONLYFANS_POST_PATTERN.match(url.strip())
    return match.group(1) if match else None


def get_creator_from_onlyfans_url(url: str) -> Optional[str]:
    """
    Extract creator username from OnlyFans URL.

    Args:
        url: OnlyFans post URL

    Returns:
        Creator username or None if not found
    """
    match = ONLYFANS_POST_PATTERN.match(url.strip())
    return match.group(2) if match else None


def get_post_id_from_of_request(requested_post: str) -> str:
    """
    Extract post ID from OnlyFans URL or return raw ID.

    Args:
        requested_post: User input (URL or raw post ID)

    Returns:
        Extracted post ID
    """
    requested_post = requested_post.strip()

    # Try URL pattern first
    post_id = get_post_id_from_onlyfans_url(requested_post)
    if post_id:
        return post_id

    # Return as-is (assume raw ID)
    return requested_post
