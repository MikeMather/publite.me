import hashlib
import hmac
import re
import secrets
from typing import Tuple

import cryptography.hazmat.primitives.asymmetric.ed25519 as ed25519
import markdown
from cryptography.hazmat.primitives import serialization


def slugify(text: str) -> str:
    """
    Convert a string to a URL-friendly slug.
    """
    text = text.lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9\-]", "", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    return text


def markdown_to_html(markdown_text: str) -> str:
    """
    Convert markdown text to HTML.
    """
    html = markdown.markdown(
        markdown_text,
        extensions=[
            "markdown.extensions.fenced_code",
            "markdown.extensions.tables",
            "markdown.extensions.codehilite",
        ],
    )
    return html


def generate_unique_slug(title: str, existing_slugs: list, attempt: int = 0) -> str:
    """
    Generate a unique slug based on the title.
    If the slug already exists, append a number.
    """
    base_slug = slugify(title)
    if attempt > 0:
        slug = f"{base_slug}-{attempt}"
    else:
        slug = base_slug

    if slug in existing_slugs:
        return generate_unique_slug(title, existing_slugs, attempt + 1)

    return slug


def generate_key_pair() -> Tuple[str, str]:
    """
    Generate a new Ed25519 key pair for blog verification.

    Returns:
        Tuple[str, str]: A tuple containing (private_key_pem, public_key_pem)
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    return private_key_pem, public_key_pem


def generate_csrf_token() -> str:
    """
    Generate a random CSRF token.

    Returns:
        str: A random token for CSRF protection
    """
    return secrets.token_hex(32)


def validate_csrf_token(token: str, secret_key: str) -> bool:
    """
    Validate a CSRF token.

    Args:
        token: The token to validate
        secret_key: The secret key used to sign the token

    Returns:
        bool: True if the token is valid, False otherwise
    """
    if not token:
        return False

    try:
        token_value, signature = token.split(":", 1)

        expected_signature = hmac.new(
            secret_key.encode(), token_value.encode(), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)
    except (ValueError, AttributeError):
        return False


def sign_csrf_token(token_value: str, secret_key: str) -> str:
    """
    Sign a CSRF token with the secret key.

    Args:
        token_value: The token value to sign
        secret_key: The secret key to use for signing

    Returns:
        str: The signed token (token_value:signature)
    """
    signature = hmac.new(
        secret_key.encode(), token_value.encode(), hashlib.sha256
    ).hexdigest()

    return f"{token_value}:{signature}"
