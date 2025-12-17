"""
Tests for the content filtering pipeline.
"""

import base64
import os
import sys
import unittest

# Add parent directory for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SCRIPT_DIR)
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

from filters.pipeline import (
    MAX_CONTENT_LENGTH,
    SecretMatch,
    decode_base64_segments,
    detect_secrets,
    filter_pipeline,
    filter_secrets,
    quick_check,
    truncate_text,
)


class TestSecretPatterns(unittest.TestCase):
    """Tests for secret detection patterns."""

    def test_aws_access_key(self):
        """Should detect AWS access keys."""
        text = "Here's my key: AKIAIOSFODNN7EXAMPLE"
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("aws_access_key", result.secret_types)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", result.filtered_text)

    def test_aws_secret_key(self):
        """Should detect AWS secret keys in standard format."""
        # The pattern requires: aws[anything]{0,20}secret[anything]{0,20}["'][40 chars]['"']
        text = 'aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"'
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("aws_secret_key", result.secret_types)

    def test_github_pat(self):
        """Should detect GitHub PATs."""
        # ghp_ followed by 36+ alphanumeric chars
        text = "token: ghp_abcdefghijklmnopqrstuvwxyz0123456789AB"
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("github_pat", result.secret_types)

    def test_github_oauth(self):
        """Should detect GitHub OAuth tokens."""
        text = "gho_abcdefghijklmnopqrstuvwxyz0123456789AB"
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("github_oauth", result.secret_types)

    def test_anthropic_key(self):
        """Should detect Anthropic API keys."""
        # Format: sk-ant-api + 2 digits + 80+ chars
        text = "ANTHROPIC_API_KEY=sk-ant-api03-" + "x" * 80
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("anthropic_key", result.secret_types)

    def test_openai_key(self):
        """Should detect OpenAI API keys."""
        # Format: sk- + 20+ chars + T3BlbkFJ + 20+ chars
        text = "openai_key: sk-xxxxxxxxxxxxxxxxxxxxT3BlbkFJyyyyyyyyyyyyyyyyyyyy"
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("openai_key", result.secret_types)

    def test_bearer_token(self):
        """Should detect Bearer tokens."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("bearer_token", result.secret_types)

    def test_private_key_header(self):
        """Should detect private key headers."""
        text = "-----BEGIN RSA PRIVATE KEY-----"
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("private_key", result.secret_types)

    def test_postgres_uri(self):
        """Should detect PostgreSQL connection URIs."""
        text = "DATABASE_URL=postgresql://user:password@localhost:5432/mydb"
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("postgres_uri", result.secret_types)

    def test_slack_token(self):
        """Should detect Slack tokens."""
        text = "xoxb-1234567890123-1234567890123-abcdefghijklmnopqrstuvwx"
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("slack_token", result.secret_types)

    def test_google_api_key(self):
        """Should detect Google API keys."""
        # Format: AIza + exactly 35 alphanumeric chars
        text = "AIzaSyC0abcdefghijklmnopqrstuvwxyz12345"  # AIza + 35 chars = 39 total
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("google_api_key", result.secret_types)

    def test_stripe_secret_key(self):
        """Should detect Stripe secret keys."""
        text = "sk_live_xxxxxxxxxxxxxxxxxxxxxxxx"
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("stripe_secret", result.secret_types)

    def test_no_false_positives_on_normal_text(self):
        """Should not flag normal text as secrets."""
        text = "This is a normal sentence without any secrets. Just some code: const x = 5;"
        result = filter_pipeline(text)
        self.assertEqual(result.secret_count, 0)
        self.assertEqual(result.filtered_text, text)

    def test_multiple_secrets(self):
        """Should detect multiple secrets in one text."""
        text = """
        AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
        DATABASE_URL=postgresql://user:pass@host/db
        """
        result = filter_pipeline(text)
        self.assertGreaterEqual(result.secret_count, 2)

    def test_replacement_format(self):
        """Secrets should be replaced with type indicators."""
        text = "My key is AKIAIOSFODNN7EXAMPLE"
        result = filter_pipeline(text)
        self.assertIn("[SECRET:aws_access_key]", result.filtered_text)

    def test_password_assignment(self):
        """Should detect password assignments."""
        text = 'password = "supersecretpassword123"'
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("password_assignment", result.secret_types)

    def test_jwt_token(self):
        """Should detect JWT tokens."""
        # JWT format: header.payload.signature (base64)
        text = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("jwt", result.secret_types)


class TestBase64Decoding(unittest.TestCase):
    """Tests for base64 secret detection bypass prevention."""

    def test_decode_base64_segments_empty(self):
        """Should return original text when no base64 content."""
        text = "Normal text without base64"
        result = decode_base64_segments(text)
        self.assertEqual(result, text)

    def test_decode_base64_segments_finds_encoded(self):
        """Should append decoded base64 content."""
        # Encode a secret
        secret = "AKIAIOSFODNN7EXAMPLE"
        encoded = base64.b64encode(secret.encode()).decode()
        text = f"Encoded secret: {encoded}"

        result = decode_base64_segments(text)

        # Should contain the decoded content
        self.assertIn("[B64_DECODED]", result)
        self.assertIn(secret, result)

    def test_decode_base64_ignores_invalid(self):
        """Should ignore invalid base64 content."""
        text = "Random text that looks like base64: AAAAAAAAAAAAAAAAAAAAAA=="
        result = decode_base64_segments(text)
        # Should not crash, may or may not decode depending on if it's valid
        self.assertIsInstance(result, str)

    def test_decode_base64_respects_max_length(self):
        """Should respect max decoded length limit."""
        # Create a large base64 encoded string
        large_content = "A" * 50000
        encoded = base64.b64encode(large_content.encode()).decode()
        text = f"Large: {encoded}"

        result = decode_base64_segments(text, max_decoded_length=100)

        # Decoded content should be limited
        if "[B64_DECODED]" in result:
            decoded_section = result.split("[B64_DECODED]")[1]
            self.assertLess(len(decoded_section.strip()), 200)

    def test_detect_base64_encoded_aws_key(self):
        """Should detect AWS key hidden in base64."""
        # Base64 encode an AWS access key
        aws_key = "AKIAIOSFODNN7EXAMPLE"
        encoded = base64.b64encode(aws_key.encode()).decode()
        text = f"Config: {encoded}"

        result = filter_pipeline(text)

        # Should detect the encoded secret
        self.assertGreater(result.secret_count, 0)
        self.assertIn("aws_access_key", result.secret_types)

    def test_detect_base64_encoded_password(self):
        """Should detect password hidden in base64."""
        # Base64 encode a password assignment
        password_text = 'password = "mysupersecretpassword"'
        encoded = base64.b64encode(password_text.encode()).decode()
        text = f"Data: {encoded}"

        result = filter_pipeline(text)

        # Should detect the encoded password
        self.assertGreater(result.secret_count, 0)
        self.assertIn("password_assignment", result.secret_types)

    def test_filter_secrets_adds_warning_for_encoded_only(self):
        """Should add warning when secrets found only in decoded content."""
        # Base64 encode a secret that's not in the original text
        aws_key = "AKIAIOSFODNN7EXAMPLE"
        encoded = base64.b64encode(aws_key.encode()).decode()
        text = f"Safe looking config: {encoded}"

        filtered_text, secret_types = filter_secrets(text)

        # Should have detected the secret
        self.assertIn("aws_access_key", secret_types)
        # Should add warning about encoded secrets
        self.assertIn("Base64-encoded secrets detected", filtered_text)

    def test_normal_base64_not_flagged(self):
        """Normal base64 content (no secrets) should not be flagged."""
        # Base64 encode something innocent
        innocent = "Hello, World! This is a test message."
        encoded = base64.b64encode(innocent.encode()).decode()
        text = f"Message: {encoded}"

        result = filter_pipeline(text)

        # Should not detect secrets
        self.assertEqual(result.secret_count, 0)


class TestTruncation(unittest.TestCase):
    """Tests for content truncation."""

    def test_short_content_not_truncated(self):
        """Short content should not be truncated."""
        text = "Short text"
        result = filter_pipeline(text)
        self.assertFalse(result.was_truncated)
        self.assertEqual(result.filtered_text, text)

    def test_long_content_truncated(self):
        """Content over limit should be truncated."""
        # Create content just over the limit
        text = "x" * 60000
        result = filter_pipeline(text)
        self.assertTrue(result.was_truncated)
        self.assertLess(len(result.filtered_text), len(text))
        self.assertIn("TRUNCATED", result.filtered_text)


class TestFilterResult(unittest.TestCase):
    """Tests for FilterResult structure."""

    def test_filter_info_conversion(self):
        """FilterResult should convert to FilterInfo."""
        text = "AKIAIOSFODNN7EXAMPLE"
        result = filter_pipeline(text)
        info = result.to_filter_info()

        self.assertEqual(info.secret_count, result.secret_count)
        self.assertEqual(info.secret_types, result.secret_types)
        self.assertEqual(info.was_truncated, result.was_truncated)

    def test_was_filtered_property(self):
        """was_filtered should be True when secrets found or truncated."""
        # With secrets
        result1 = filter_pipeline("AKIAIOSFODNN7EXAMPLE")
        self.assertTrue(result1.was_filtered)

        # Without anything
        result2 = filter_pipeline("Normal text")
        self.assertFalse(result2.was_filtered)


class TestDetectSecrets(unittest.TestCase):
    """Tests for detect_secrets function."""

    def test_returns_secret_match_objects(self):
        """Should return SecretMatch objects with position info."""
        text = "Key: AKIAIOSFODNN7EXAMPLE"
        matches = detect_secrets(text)

        self.assertEqual(len(matches), 1)
        match = matches[0]
        self.assertEqual(match.secret_type, "aws_access_key")
        self.assertIn("AKIAIOSFODNN7EXAMPLE", match.match)
        self.assertGreaterEqual(match.start, 0)
        self.assertLessEqual(match.end, len(text))

    def test_matches_sorted_by_position(self):
        """Matches should be sorted by start position."""
        text = "First: AKIAIOSFODNN7EXAMPLE, Second: postgresql://user:pass@host/db"
        matches = detect_secrets(text)

        # Should have at least 2 matches
        self.assertGreaterEqual(len(matches), 2)

        # Should be sorted by position
        positions = [m.start for m in matches]
        self.assertEqual(positions, sorted(positions))


# ============================================================================
# NEW TESTS ADDED FOR COVERAGE GAPS
# ============================================================================


class TestDetectSecretsDirectly(unittest.TestCase):
    """Direct tests for detect_secrets() function - verifying SecretMatch objects."""

    def test_secret_match_has_correct_positions(self):
        """Verify SecretMatch objects contain correct start and end positions."""
        text = "prefix AKIAIOSFODNN7EXAMPLE suffix"
        matches = detect_secrets(text)

        self.assertEqual(len(matches), 1)
        match = matches[0]

        # Verify the match object structure
        self.assertIsInstance(match, SecretMatch)
        self.assertEqual(match.secret_type, "aws_access_key")
        self.assertEqual(match.match, "AKIAIOSFODNN7EXAMPLE")
        # The key starts at position 7 (after "prefix ")
        self.assertEqual(match.start, 7)
        self.assertEqual(match.end, 7 + len("AKIAIOSFODNN7EXAMPLE"))

    def test_detect_secrets_empty_text(self):
        """Should return empty list for empty text."""
        matches = detect_secrets("")
        self.assertEqual(matches, [])

    def test_detect_secrets_no_secrets(self):
        """Should return empty list for text without secrets."""
        matches = detect_secrets("This is normal text without any secrets.")
        self.assertEqual(matches, [])

    def test_detect_secrets_multiple_same_type(self):
        """Should detect multiple secrets of the same type."""
        text = "Key1: AKIAIOSFODNN7EXAMPLE Key2: AKIAIOSFODNN7EXAMPL2"
        matches = detect_secrets(text)

        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0].secret_type, "aws_access_key")
        self.assertEqual(matches[1].secret_type, "aws_access_key")
        self.assertLess(matches[0].start, matches[1].start)


class TestFilterSecretsDirectly(unittest.TestCase):
    """Direct tests for filter_secrets() function - verifying replacement format."""

    def test_replacement_format_contains_secret_type(self):
        """Verify replacement format is [SECRET:type]."""
        text = "My AWS key is AKIAIOSFODNN7EXAMPLE here"
        filtered_text, secret_types = filter_secrets(text)

        self.assertEqual(secret_types, ["aws_access_key"])
        self.assertIn("[SECRET:aws_access_key]", filtered_text)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", filtered_text)

    def test_filter_secrets_preserves_surrounding_text(self):
        """Verify surrounding text is preserved."""
        text = "Before AKIAIOSFODNN7EXAMPLE After"
        filtered_text, _ = filter_secrets(text)

        self.assertTrue(filtered_text.startswith("Before "))
        self.assertTrue(filtered_text.endswith(" After"))

    def test_filter_secrets_multiple_replacements(self):
        """Verify multiple secrets are all replaced."""
        text = "Key: AKIAIOSFODNN7EXAMPLE DB: postgresql://user:pass@host/db"
        filtered_text, secret_types = filter_secrets(text)

        self.assertIn("aws_access_key", secret_types)
        self.assertIn("postgres_uri", secret_types)
        self.assertIn("[SECRET:aws_access_key]", filtered_text)
        self.assertIn("[SECRET:postgres_uri]", filtered_text)

    def test_filter_secrets_returns_empty_list_when_no_secrets(self):
        """Should return empty list when no secrets found."""
        text = "Normal text without secrets"
        filtered_text, secret_types = filter_secrets(text)

        self.assertEqual(filtered_text, text)
        self.assertEqual(secret_types, [])


class TestTruncateTextDirectly(unittest.TestCase):
    """Direct tests for truncate_text() function - verifying max_length parameter."""

    def test_truncate_text_below_limit(self):
        """Text below max_length should not be truncated."""
        text = "Short text"
        result, was_truncated = truncate_text(text, max_length=100)

        self.assertEqual(result, text)
        self.assertFalse(was_truncated)

    def test_truncate_text_at_exact_limit(self):
        """Text at exact max_length should not be truncated."""
        text = "x" * 100
        result, was_truncated = truncate_text(text, max_length=100)

        self.assertEqual(result, text)
        self.assertFalse(was_truncated)

    def test_truncate_text_above_limit(self):
        """Text above max_length should be truncated."""
        text = "x" * 200
        result, was_truncated = truncate_text(text, max_length=100)

        self.assertTrue(was_truncated)
        self.assertLess(len(result), len(text))
        self.assertIn("TRUNCATED", result)

    def test_truncate_text_custom_max_length(self):
        """Verify custom max_length parameter is respected."""
        text = "x" * 50
        result, was_truncated = truncate_text(text, max_length=30)

        self.assertTrue(was_truncated)
        self.assertIn("TRUNCATED", result)

    def test_truncate_text_shows_removed_count(self):
        """Truncation notice should show how many chars were removed."""
        text = "x" * 1000
        result, _ = truncate_text(text, max_length=500)

        # The truncation notice contains the count of removed characters
        self.assertIn("TRUNCATED", result)
        self.assertIn("chars removed", result)

    def test_truncate_text_default_max_length(self):
        """Test truncation with default MAX_CONTENT_LENGTH."""
        text = "x" * (MAX_CONTENT_LENGTH + 1000)
        result, was_truncated = truncate_text(text)

        self.assertTrue(was_truncated)
        self.assertLess(len(result), MAX_CONTENT_LENGTH + 1000)


class TestQuickCheckDirectly(unittest.TestCase):
    """Direct tests for quick_check() function - verifying fast pre-filter logic."""

    def test_quick_check_returns_true_for_secrets(self):
        """quick_check should return True when secrets are present."""
        text = "My AWS key is AKIAIOSFODNN7EXAMPLE"
        result = quick_check(text)
        self.assertTrue(result)

    def test_quick_check_returns_false_for_clean_text(self):
        """quick_check should return False for clean text."""
        text = "This is normal text without any secrets."
        result = quick_check(text)
        self.assertFalse(result)

    def test_quick_check_returns_true_for_truncated_content(self):
        """quick_check should return True when content would be truncated."""
        text = "x" * (MAX_CONTENT_LENGTH + 1000)
        result = quick_check(text)
        self.assertTrue(result)

    def test_quick_check_empty_text(self):
        """quick_check should return False for empty text."""
        result = quick_check("")
        self.assertFalse(result)

    def test_quick_check_with_base64_encoded_secret(self):
        """quick_check should detect base64 encoded secrets."""
        aws_key = "AKIAIOSFODNN7EXAMPLE"
        encoded = base64.b64encode(aws_key.encode()).decode()
        text = f"Encoded: {encoded}"
        result = quick_check(text)
        self.assertTrue(result)


class TestDatabaseURIPatterns(unittest.TestCase):
    """Tests for MySQL, MongoDB, and Redis URI pattern detection."""

    def test_mysql_uri_basic(self):
        """Should detect basic MySQL connection URI."""
        text = "DATABASE_URL=mysql://user:password@localhost:3306/mydb"
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("mysql_uri", result.secret_types)

    def test_mysql_uri_without_port(self):
        """Should detect MySQL URI without explicit port."""
        text = "mysql://root:secret@db.example.com/production"
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("mysql_uri", result.secret_types)

    def test_mysql_uri_replacement(self):
        """MySQL URI should be replaced with placeholder."""
        text = "Connect to mysql://user:pass@host/db for data"
        result = filter_pipeline(text)
        self.assertIn("[SECRET:mysql_uri]", result.filtered_text)
        self.assertNotIn("mysql://user:pass@host/db", result.filtered_text)

    def test_mongodb_uri_basic(self):
        """Should detect basic MongoDB connection URI."""
        text = "MONGO_URL=mongodb://user:password@localhost:27017/mydb"
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("mongodb_uri", result.secret_types)

    def test_mongodb_srv_uri(self):
        """Should detect MongoDB+srv URI (Atlas style)."""
        text = "mongodb+srv://admin:secretpass@cluster0.example.mongodb.net/mydb"
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("mongodb_uri", result.secret_types)

    def test_mongodb_uri_with_options(self):
        """Should detect MongoDB URI with connection options."""
        text = "mongodb://user:pass@host1:27017,host2:27017/db?replicaSet=rs0"
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("mongodb_uri", result.secret_types)

    def test_redis_uri_basic(self):
        """Should detect basic Redis connection URI."""
        text = "REDIS_URL=redis://default:password@localhost:6379/0"
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("redis_uri", result.secret_types)

    def test_redis_uri_without_password(self):
        """Should detect Redis URI without password."""
        text = "redis://localhost:6379/0"
        result = filter_pipeline(text)
        self.assertGreater(result.secret_count, 0)
        self.assertIn("redis_uri", result.secret_types)

    def test_redis_uri_replacement(self):
        """Redis URI should be replaced with placeholder."""
        text = "Cache at redis://user:secret@cache.example.com:6379"
        result = filter_pipeline(text)
        self.assertIn("[SECRET:redis_uri]", result.filtered_text)

    def test_multiple_database_uris(self):
        """Should detect multiple different database URIs."""
        text = """
        MYSQL_URL=mysql://user:pass@mysql.host/db
        MONGO_URL=mongodb://user:pass@mongo.host/db
        REDIS_URL=redis://user:pass@redis.host:6379
        """
        result = filter_pipeline(text)
        self.assertGreaterEqual(result.secret_count, 3)
        self.assertIn("mysql_uri", result.secret_types)
        self.assertIn("mongodb_uri", result.secret_types)
        self.assertIn("redis_uri", result.secret_types)


class TestSecretMatchDataclass(unittest.TestCase):
    """Tests for SecretMatch dataclass structure."""

    def test_secret_match_fields(self):
        """Verify SecretMatch has all expected fields."""
        match = SecretMatch(
            secret_type="test_type",
            match="test_match",
            start=0,
            end=10,
        )
        self.assertEqual(match.secret_type, "test_type")
        self.assertEqual(match.match, "test_match")
        self.assertEqual(match.start, 0)
        self.assertEqual(match.end, 10)

    def test_secret_match_equality(self):
        """Verify SecretMatch equality works correctly."""
        match1 = SecretMatch(secret_type="type", match="value", start=0, end=5)
        match2 = SecretMatch(secret_type="type", match="value", start=0, end=5)
        self.assertEqual(match1, match2)


if __name__ == "__main__":
    unittest.main()
