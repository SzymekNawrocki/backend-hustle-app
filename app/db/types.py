from datetime import datetime
from sqlalchemy import DateTime, TypeDecorator

class NaiveDateTime(TypeDecorator):
    """
    SQLAlchemy type that ensures datetimes are naive before binding to parameters.
    Prevents 'can't subtract offset-naive and offset-aware datetimes' with asyncpg
    and TIMESTAMP WITHOUT TIME ZONE columns.
    """
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and hasattr(value, "tzinfo") and value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value
