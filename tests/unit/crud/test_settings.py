from sqlalchemy.orm import Session

from app.crud.settings import get_settings, update_settings
from app.models import Settings
from app.schemas import SettingsUpdate


def test_get_settings(db_session: Session):
    settings = get_settings(db_session)

    # Verify default settings are created when none exist
    assert settings.blog_title == "My Blog"
    assert settings.blog_description == "A minimalist blog"
    assert settings.custom_css == ""
    assert settings.theme == "default"
    assert settings.navigation_markdown == "[Home](/)"
    assert settings.footer_markdown == "Powered by publite.me"
    assert settings.comments_enabled is True
    assert settings.allow_anonymous_comments is False

    db_settings = db_session.query(Settings).first()
    assert db_settings is not None
    assert db_settings.blog_title == settings.blog_title
    assert db_settings.blog_description == settings.blog_description


def test_update_settings(db_session: Session):
    initial_settings = get_settings(db_session)
    assert initial_settings is not None

    update_data = SettingsUpdate(
        blog_title="Updated Blog",
        blog_description="Updated description",
        custom_css="body { background-color: red; }",
        theme="light",
        navigation_markdown="[Home](/) [About](/about)",
        footer_markdown="Updated footer",
        comments_enabled=False,
        allow_anonymous_comments=True,
    )

    updated_settings = update_settings(db_session, update_data)

    assert updated_settings.blog_title == update_data.blog_title
    assert updated_settings.blog_description == update_data.blog_description
    assert updated_settings.custom_css == update_data.custom_css
    assert updated_settings.theme == update_data.theme
    assert updated_settings.navigation_markdown == update_data.navigation_markdown
    assert updated_settings.footer_markdown == update_data.footer_markdown
    assert updated_settings.comments_enabled == update_data.comments_enabled
    assert (
        updated_settings.allow_anonymous_comments
        == update_data.allow_anonymous_comments
    )

    db_settings = db_session.query(Settings).first()
    assert db_settings is not None
    assert db_settings.blog_title == update_data.blog_title
    assert db_settings.blog_description == update_data.blog_description
    assert db_settings.custom_css == update_data.custom_css
    assert db_settings.theme == update_data.theme
    assert db_settings.navigation_markdown == update_data.navigation_markdown
    assert db_settings.footer_markdown == update_data.footer_markdown
    assert db_settings.comments_enabled == update_data.comments_enabled
    assert db_settings.allow_anonymous_comments == update_data.allow_anonymous_comments
