import pytest

from app.utils import (
    generate_csrf_token,
    generate_key_pair,
    generate_unique_slug,
    markdown_to_html,
    sign_csrf_token,
    slugify,
    validate_csrf_token,
)


def test_slugify():
    assert slugify("Hello World") == "hello-world"
    assert slugify("Test@#Special$%Chars") == "testspecialchars"
    assert slugify("Multiple   Spaces") == "multiple-spaces"
    assert slugify("  Trim Me  ") == "trim-me"
    assert slugify("Already---hyphenated") == "already-hyphenated"


def test_markdown_to_html():
    assert markdown_to_html("# Heading") == "<h1>Heading</h1>"
    markdown = "```python\nprint('Hello')\n```"
    expected_html = (
        '<div class="codehilite"><pre><span></span><code>'
        '<span class="nb">print</span><span class="p">(</span>'
        '<span class="s1">&#39;Hello&#39;</span><span class="p">)</span>\n'
        "</code></pre></div>"
    )
    assert markdown_to_html(markdown) == expected_html
    markdown = "| Header |\n|--------|\n| Cell   |"
    expected_html = (
        "<table>\n<thead>\n<tr>\n<th>Header</th>\n</tr>\n</thead>\n"
        "<tbody>\n<tr>\n<td>Cell</td>\n</tr>\n</tbody>\n</table>"
    )
    assert markdown_to_html(markdown) == expected_html


def test_generate_unique_slug():
    existing_slugs = ["test", "test-1", "test-2"]
    assert generate_unique_slug("Test", existing_slugs) == "test-3"
    assert generate_unique_slug("Test", ["test"]) == "test-1"
    assert generate_unique_slug("Test", ["test", "test-1", "test-2"]) == "test-3"


def test_generate_key_pair():
    private_key, public_key = generate_key_pair()
    assert private_key.startswith("-----BEGIN PRIVATE KEY-----")
    assert public_key.startswith("-----BEGIN PUBLIC KEY-----")
    assert len(private_key) > 100
    assert len(public_key) > 100


def test_csrf_token_flow():
    token = generate_csrf_token()
    assert len(token) == 64
    secret_key = "test-secret"
    signed_token = sign_csrf_token(token, secret_key)
    assert validate_csrf_token(signed_token, secret_key) is True
    assert validate_csrf_token("invalid:token", secret_key) is False
    tampered_token = signed_token.replace("a", "b")
    assert validate_csrf_token(tampered_token, secret_key) is False


@pytest.mark.parametrize(
    "input,expected",
    [
        ("Test String", "test-string"),
        ("  Trim Me  ", "trim-me"),
        ("Special@Chars", "specialchars"),
        ("Multiple   Spaces", "multiple-spaces"),
        ("Already---hyphenated", "already-hyphenated"),
    ],
)
def test_slugify_parametrized(input, expected):
    assert slugify(input) == expected
