"""
Tests for the content filtering pipeline.
"""

import os
import sys
import unittest

# Add parent directory for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SCRIPT_DIR)
if PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, PLUGIN_ROOT)

from filters.pipeline import filter_pipeline, SECRET_PATTERNS


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


if __name__ == "__main__":
    unittest.main()
