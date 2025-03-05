from sqlalchemy.orm import Session

from app.models import Settings
from app.utils import generate_key_pair


def get_settings(db: Session) -> Settings:
    settings = db.query(Settings).first()
    if not settings:
        private_key_pem, public_key_pem = generate_key_pair()

        settings = Settings(
            blog_title="My Blog",
            blog_description="A minimalist blog",
            custom_css="",
            theme="default",
            navigation_markdown="[Home](/)",
            footer_markdown="Powered by publite.me",
            private_key=private_key_pem,
            public_key=public_key_pem,
            comments_enabled=True,
            allow_anonymous_comments=False,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def update_settings(db: Session, settings_update) -> Settings:
    db_settings = db.query(Settings).first()
    if not db_settings:
        db_settings = Settings()
        db.add(db_settings)

    update_data = settings_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_settings, key, value)

    db.commit()
    db.refresh(db_settings)
    return db_settings
