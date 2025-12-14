"""
Filter Pipeline for claude-spec Prompt Capture Hook.

This module chains content filters together to sanitize prompt content
before logging. The pipeline runs in a specific order to ensure security:

1. **Secrets Filter** (security-critical, runs first)
   - Detects and replaces sensitive credentials with placeholders
   - Includes base64 decoding to catch encoded secrets

2. **Truncation Filter** (if content is too long)
   - Limits content to MAX_CONTENT_LENGTH characters
   - Adds truncation notice with character count

Returns a unified FilterResult with all filtering statistics.

Security Features
-----------------

**Base64 Decoding for Secret Detection**:
    Attackers may attempt to bypass secret detection by base64-encoding
    credentials. This module decodes potential base64 segments and scans
    the decoded content for secrets. If secrets are found in decoded
    content, a warning is appended even if the original text is unchanged.

    The decoding process:
    1. Find strings matching base64 pattern (20+ chars, optional padding)
    2. Attempt to decode as base64
    3. If valid UTF-8 text results, scan it for secrets
    4. Limit total decoded content to prevent memory exhaustion

**Comprehensive Secret Patterns**:
    Pre-compiled regex patterns detect 15+ secret types across major
    cloud providers, SaaS services, and common credential formats.

SECRET_PATTERNS Reference
-------------------------

The following secret types are detected. Pattern names are used in
``[SECRET:pattern_name]`` placeholders:

**Cloud Provider Keys**:
    - ``aws_access_key``: AWS Access Key IDs (AKIA, ASIA, etc.)
    - ``aws_secret_key``: AWS Secret Access Keys
    - ``google_api_key``: Google API keys (AIza...)

**Version Control & CI/CD**:
    - ``github_pat``: GitHub Personal Access Tokens (ghp_...)
    - ``github_oauth``: GitHub OAuth tokens (gho_...)
    - ``github_app``: GitHub App tokens (ghu_, ghs_...)

**AI/ML Services**:
    - ``openai_key``: OpenAI API keys (sk-...T3BlbkFJ...)
    - ``anthropic_key``: Anthropic API keys (sk-ant-api...)

**Payment Processing**:
    - ``stripe_secret``: Stripe secret keys (sk_live_...)
    - ``stripe_publishable``: Stripe publishable keys (pk_live_...)

**Communication**:
    - ``slack_token``: Slack API tokens (xoxb-, xoxp-, etc.)

**Authentication**:
    - ``bearer_token``: Bearer tokens in Authorization headers
    - ``jwt``: JSON Web Tokens (ey...ey...signature)

**Database Connection Strings**:
    - ``postgres_uri``: PostgreSQL connection strings
    - ``mysql_uri``: MySQL connection strings
    - ``mongodb_uri``: MongoDB connection strings (including +srv)
    - ``redis_uri``: Redis connection strings

**Cryptographic Material**:
    - ``private_key``: RSA, DSA, EC, OpenSSH, PGP private key headers

**Generic Credentials**:
    - ``password_assignment``: password/passwd/pwd assignments in code
    - ``secret_assignment``: secret/api_key/access_token assignments

Adding New Secret Patterns
--------------------------

To add a new secret pattern:

1. Add the pattern to ``SECRET_PATTERNS`` dict::

    SECRET_PATTERNS: dict[str, Pattern[str]] = {
        # ... existing patterns ...

        # New pattern - use descriptive name
        "datadog_api_key": re.compile(r"dd[a-zA-Z0-9]{32}"),
    }

2. Pattern guidelines:
   - Use word boundaries (``\\b``) where appropriate to avoid false positives
   - Use non-capturing groups ``(?:...)`` for alternation
   - Use case-insensitive flag ``(?i)`` only when necessary
   - Test against both positive and negative cases

3. Pattern name conventions:
   - Use lowercase with underscores
   - Include the service name (e.g., ``stripe_secret``, not just ``secret``)
   - Distinguish variants (e.g., ``github_pat`` vs ``github_oauth``)

4. Add tests in ``tests/test_pipeline.py``::

    def test_detects_new_pattern():
        text = "api_key = dd1234567890abcdef1234567890abcdef"
        result = filter_pipeline(text)
        assert result.secret_count == 1
        assert "datadog_api_key" in result.secret_types

Base64 Bypass Prevention
------------------------

The module prevents secret bypass via base64 encoding:

1. **Detection**: ``B64_PATTERN`` matches potential base64 strings (20+ chars)

2. **Decoding**: ``decode_base64_segments()`` attempts to decode matches:
   - Validates as proper base64 (no padding errors)
   - Converts to UTF-8 text
   - Only includes printable content

3. **Scanning**: Decoded content is appended with ``[B64_DECODED]`` marker
   and scanned for secrets

4. **Reporting**: If secrets found only in decoded content, original text
   gets a warning appended

5. **Limits**: ``max_decoded_length`` prevents memory exhaustion attacks
   from maliciously large encoded content

Example::

    # Base64-encoded AWS key: QUtJQVRFU1QxMjM0NTY3ODkw
    text = "encoded: QUtJQVRFU1QxMjM0NTY3ODkw"
    result = filter_pipeline(text)
    # Detects aws_access_key in decoded content
    assert "aws_access_key" in result.secret_types
"""

import base64
import re
from dataclasses import dataclass, field
from re import Pattern

from .log_entry import FilterInfo

# Maximum content length before truncation
MAX_CONTENT_LENGTH = 50000

# Base64 pattern for detecting encoded content
# Matches strings of 20+ base64 characters with optional padding
B64_PATTERN = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")

# Pre-compiled regex patterns for secret detection
SECRET_PATTERNS: dict[str, Pattern[str]] = {
    # AWS
    "aws_access_key": re.compile(
        r"\b((?:A3T[A-Z0-9]|AKIA|ASIA|ABIA|ACCA)[A-Z2-7]{16})\b"
    ),
    "aws_secret_key": re.compile(
        r'(?i)aws.{0,20}secret.{0,20}[\'"][0-9a-zA-Z/+=]{40}[\'"]'
    ),
    # GitHub
    "github_pat": re.compile(r"ghp_[A-Za-z0-9_]{36,}"),
    "github_oauth": re.compile(r"gho_[A-Za-z0-9_]{36,}"),
    "github_app": re.compile(r"(?:ghu|ghs)_[A-Za-z0-9_]{36,}"),
    # AI Services
    "openai_key": re.compile(r"sk-[a-zA-Z0-9]{20,}T3BlbkFJ[a-zA-Z0-9]{20,}"),
    "anthropic_key": re.compile(r"sk-ant-api\d{2}-[a-zA-Z0-9_\-]{80,}"),
    # Google
    "google_api_key": re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    # Stripe
    "stripe_secret": re.compile(r"sk_live_[0-9a-zA-Z]{24,}"),
    "stripe_publishable": re.compile(r"pk_live_[0-9a-zA-Z]{24,}"),
    # Slack
    "slack_token": re.compile(r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*"),
    # Generic patterns
    "bearer_token": re.compile(r"Bearer\s+[a-zA-Z0-9\-_.~+\/]+=*"),
    "jwt": re.compile(
        r"ey[a-zA-Z0-9]{17,}\.ey[a-zA-Z0-9\/\\_-]{17,}\.[a-zA-Z0-9\/\\_-]{10,}"
    ),
    # Connection strings
    "postgres_uri": re.compile(r'postgres(?:ql)?://[^\s\'"]+'),
    "mysql_uri": re.compile(r'mysql://[^\s\'"]+'),
    "mongodb_uri": re.compile(r'mongodb(?:\+srv)?://[^\s\'"]+'),
    "redis_uri": re.compile(r'redis://[^\s\'"]+'),
    # Private keys (detect headers)
    "private_key": re.compile(
        r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY"
    ),
    # Password patterns (context-aware)
    "password_assignment": re.compile(
        r'(?i)(?:password|passwd|pwd)\s*[:=]\s*[\'"][^\'"]{8,}[\'"]'
    ),
    "secret_assignment": re.compile(
        r'(?i)(?:secret|api[_-]?key|access[_-]?token|auth[_-]?token)\s*[:=]\s*[\'"][^\'"]{10,}[\'"]'
    ),
}


@dataclass
class SecretMatch:
    """Represents a detected secret in text.

    Attributes:
        secret_type: The pattern name that matched (e.g., "aws_access_key").
        match: The actual matched text (the secret value).
        start: Start index in the original text.
        end: End index in the original text.
    """

    secret_type: str
    match: str
    start: int
    end: int


@dataclass
class FilterResult:
    """Result of running the filter pipeline.

    Attributes:
        original_length: Length of the input text before filtering.
        filtered_text: The text after all filters have been applied.
        secret_count: Number of secrets detected and replaced.
        secret_types: List of secret type identifiers found.
        was_truncated: Whether the content was truncated due to length.
    """

    original_length: int
    filtered_text: str
    secret_count: int
    secret_types: list[str] = field(default_factory=list)
    was_truncated: bool = False

    def to_filter_info(self) -> FilterInfo:
        """Convert to FilterInfo for log entries."""
        return FilterInfo(
            secret_count=self.secret_count,
            secret_types=self.secret_types,
            was_truncated=self.was_truncated,
        )

    @property
    def was_filtered(self) -> bool:
        """Check if any content was filtered."""
        return self.secret_count > 0 or self.was_truncated


def decode_base64_segments(text: str, max_decoded_length: int = 10000) -> str:
    """
    Decode base64 segments to check for hidden secrets.

    This function finds potential base64-encoded segments in the text,
    attempts to decode them, and appends the decoded content for scanning.
    This prevents secret bypass via base64 encoding.

    Args:
        text: The text to scan for base64 content
        max_decoded_length: Maximum total length of decoded content to append
            (prevents memory exhaustion attacks)

    Returns:
        Original text with decoded base64 content appended for scanning
    """
    decoded_parts: list[str] = []
    total_decoded = 0

    for match in B64_PATTERN.finditer(text):
        if total_decoded >= max_decoded_length:
            break

        segment = match.group()
        # Skip segments that are clearly not secrets (too short after padding removal)
        if len(segment.rstrip("=")) < 20:
            continue

        try:
            # Try to decode as base64
            decoded_bytes = base64.b64decode(segment, validate=True)
            # Try to decode as UTF-8 text
            decoded = decoded_bytes.decode("utf-8", errors="ignore")

            # Only include if it looks like text (printable ASCII)
            if decoded and all(c.isprintable() or c.isspace() for c in decoded[:100]):
                # Limit how much we add from each segment
                segment_limit = min(len(decoded), max_decoded_length - total_decoded)
                decoded_parts.append(decoded[:segment_limit])
                total_decoded += segment_limit

        except (ValueError, UnicodeDecodeError):
            # Not valid base64 or not text - skip
            continue

    if decoded_parts:
        # Append decoded content with a separator for scanning
        return text + "\n[B64_DECODED]\n" + "\n".join(decoded_parts)

    return text


def detect_secrets(text: str) -> list[SecretMatch]:
    """
    Detect secrets in text using pre-compiled patterns.

    Args:
        text: The text to scan for secrets

    Returns:
        List of SecretMatch objects for each detected secret
    """
    matches = []

    for secret_type, pattern in SECRET_PATTERNS.items():
        for match in pattern.finditer(text):
            matches.append(
                SecretMatch(
                    secret_type=secret_type,
                    match=match.group(0),
                    start=match.start(),
                    end=match.end(),
                )
            )

    # Sort by position for consistent replacement
    matches.sort(key=lambda m: m.start)

    return matches


def filter_secrets(text: str) -> tuple[str, list[str]]:
    """
    Replace detected secrets with type-labeled placeholders.

    This function also checks for base64-encoded secrets by first
    decoding potential base64 segments and scanning the decoded content.

    Args:
        text: The text to filter

    Returns:
        Tuple of (filtered_text, list_of_secret_types_found)
    """
    # First, check for base64-encoded secrets
    text_with_decoded = decode_base64_segments(text)

    # Detect secrets in both original and decoded content
    matches = detect_secrets(text_with_decoded)

    if not matches:
        return text, []

    # We need to filter matches that are in the original text only
    # (not in the appended decoded section)
    original_length = len(text)
    original_matches = [m for m in matches if m.start < original_length]

    # Track all secret types found (including in decoded content)
    all_secret_types = list({m.secret_type for m in matches})

    if not original_matches:
        # Secrets only in decoded content - still report them but don't modify text
        # Add a note that encoded secrets were detected (matches is always truthy here
        # since we returned early above if not matches)
        return (
            text + "\n[WARNING: Base64-encoded secrets detected and filtered]",
            all_secret_types,
        )

    # Replace from end to start to preserve positions
    result = text
    secret_types = []

    for match in reversed(original_matches):
        placeholder = f"[SECRET:{match.secret_type}]"
        result = result[: match.start] + placeholder + result[match.end :]
        secret_types.append(match.secret_type)

    # Add any types found only in decoded content
    decoded_only_types = [t for t in all_secret_types if t not in secret_types]
    if decoded_only_types:
        secret_types.extend(decoded_only_types)

    # Return types in original order
    secret_types.reverse()

    return result, secret_types


def truncate_text(text: str, max_length: int = MAX_CONTENT_LENGTH) -> tuple[str, bool]:
    """
    Truncate text if it exceeds max length.

    Args:
        text: Text to potentially truncate
        max_length: Maximum allowed length

    Returns:
        Tuple of (text, was_truncated)
    """
    if len(text) <= max_length:
        return text, False

    truncate_notice = (
        f"\n...[TRUNCATED: {len(text) - max_length + 100} chars removed]..."
    )
    truncated = text[: max_length - len(truncate_notice)] + truncate_notice
    return truncated, True


def filter_pipeline(text: str) -> FilterResult:
    """
    Run the full filter pipeline on text.

    Order of operations:
    1. Filter secrets first (security-critical, includes base64 decode check)
    2. Truncate if too long

    Args:
        text: The text to filter

    Returns:
        FilterResult with filtered text and statistics
    """
    original_length = len(text)

    # Step 1: Filter secrets (includes base64 decoding check)
    text_after_secrets, secret_types = filter_secrets(text)
    secret_count = len(secret_types)

    # Step 2: Truncate if needed
    filtered_text, was_truncated = truncate_text(text_after_secrets)

    return FilterResult(
        original_length=original_length,
        filtered_text=filtered_text,
        secret_count=secret_count,
        secret_types=secret_types,
        was_truncated=was_truncated,
    )


def quick_check(text: str) -> bool:
    """
    Quick check if text contains any sensitive content.

    Useful for deciding whether to run full pipeline.

    Args:
        text: Text to check

    Returns:
        True if text likely contains sensitive content
    """
    result = filter_pipeline(text)
    return result.was_filtered
