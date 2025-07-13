from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from config import Config
from contextlib import contextmanager

# Настройка подключения к базе данных
DATABASE_URL = Config.DATABASE_URL
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(bind=engine)


def get_session():
    """Получение новой сессии базы данных"""
    return SessionLocal()


@contextmanager
def get_db_session():
    """Контекстный менеджер для работы с сессией БД"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Для обратной совместимости
def get_db():
    """Генератор сессии (для совместимости с FastAPI стилем)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()