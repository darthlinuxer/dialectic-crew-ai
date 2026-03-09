"""Tests for _slugify() and _parse_frontmatter() in dialectic.export."""

from dialectic.export import _slugify, _parse_frontmatter


class TestSlugify:
    def test_normal_text(self):
        assert _slugify("My Feature Name") == "my-feature-name"

    def test_special_characters(self):
        assert _slugify("Login & Auth (2FA)") == "login-auth-2fa"

    def test_empty_string(self):
        assert _slugify("") == "prd"

    def test_none_input(self):
        assert _slugify(None) == "prd"

    def test_already_slugged(self):
        assert _slugify("my-feature") == "my-feature"

    def test_multiple_consecutive_specials(self):
        assert _slugify("a!!!b---c") == "a-b-c"

    def test_leading_trailing_specials(self):
        assert _slugify("---hello---") == "hello"


class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        md = "---\nquality_score: 9.0\nstatus: approved\n---\n# Body"
        result = _parse_frontmatter(md)
        assert "quality_score" in result
        assert "status" in result

    def test_no_frontmatter(self):
        md = "# Just a heading\n\nSome content"
        assert _parse_frontmatter(md) == {}

    def test_empty_string(self):
        assert _parse_frontmatter("") == {}

    def test_none_input(self):
        assert _parse_frontmatter(None) == {}

    def test_incomplete_frontmatter(self):
        md = "---\nquality_score: 9.0\n"
        assert _parse_frontmatter(md) == {}

    def test_empty_yaml_block(self):
        md = "---\n---\n# Body"
        result = _parse_frontmatter(md)
        assert result == {} or isinstance(result, dict)

    def test_frontmatter_with_leading_whitespace(self):
        md = "  \n---\nkey: value\n---\nbody"
        result = _parse_frontmatter(md)
        assert "key" in result
