from datetime import datetime

from sqlalchemy.orm import Session

from backend.db.models import ReviewSettings
from backend.schemas import ReviewSettingsResponse


def get_review_settings(user_id: int, db: Session) -> ReviewSettingsResponse:
    settings = db.query(ReviewSettings).filter(ReviewSettings.user_id == user_id).first()
    return ReviewSettingsResponse(review_rules=settings.review_rules if settings else "")


def update_review_settings(user_id: int, review_rules: str, db: Session) -> ReviewSettingsResponse:
    settings = db.query(ReviewSettings).filter(ReviewSettings.user_id == user_id).first()
    rules = review_rules.strip()
    if settings:
        settings.review_rules = rules
        settings.updated_at = datetime.utcnow()
    else:
        settings = ReviewSettings(user_id=user_id, review_rules=rules)
        db.add(settings)
    db.commit()
    return ReviewSettingsResponse(review_rules=rules)
