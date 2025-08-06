import re
from urllib.parse import urlparse


class ContentValidator:
    """Simple validator to avoid spam and unwanted content."""

    #: Words that immediately mark the text as spam
    forbidden = ["spam", "scam"]

    #: Maximum length of an allowed text
    max_length = 1000

    #: Domains that are not allowed to appear in URLs
    blacklisted_domains = set()

    @staticmethod
    def _strip_markup(text: str) -> str:
        """Remove simple markdown and HTML tags from *text*."""
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"[`*_]", "", text)
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        return text

    @classmethod
    def is_valid(cls, text: str, strip_markup: bool = False) -> bool:
        """Return ``True`` if *text* passes validation checks."""

        if strip_markup:
            text = cls._strip_markup(text)

        if len(text) > cls.max_length:
            return False

        lower = text.lower()
        if any(word in lower for word in cls.forbidden):
            return False

        for url in re.findall(r"https?://[^\s]+", text):
            domain = urlparse(url).netloc.split(":")[0].lower()
            if domain in cls.blacklisted_domains:
                return False

        return True
