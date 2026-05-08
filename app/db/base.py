from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Model imports are handled in alembic/env.py to avoid circular imports
