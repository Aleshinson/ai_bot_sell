from sqlalchemy import Column, Integer, String, DateTime, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from config import Config
import datetime

Base = declarative_base()


class Announcement(Base):
    """Модель объявления"""
    __tablename__ = 'announcements'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    chat_id = Column(Integer, nullable=False)
    bot_name = Column(String, nullable=False)
    bot_function = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_approved = Column(Boolean, default=None)  # None - pending, True - approved, False - rejected
    moderator_id = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<Announcement(id={self.id}, bot_name='{self.bot_name}', is_approved={self.is_approved})>"

    @property
    def status_text(self) -> str:
        """Текстовое представление статуса"""
        if self.is_approved is None:
            return "На модерации"
        elif self.is_approved:
            return "Одобрено"
        else:
            return "Отклонено"

    def is_pending(self) -> bool:
        """Проверка, находится ли объявление на модерации"""
        return self.is_approved is None

    def is_approved_status(self) -> bool:
        """Проверка, одобрено ли объявление"""
        return self.is_approved is True

    def is_rejected(self) -> bool:
        """Проверка, отклонено ли объявление"""
        return self.is_approved is False


class BotInfo(Base):
    """Модель информации о боте (из старого файла model.py)"""
    __tablename__ = "bot_info"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    functionality = Column(String, nullable=False)


# Создание базы данных
def create_tables():
    """Создание таблиц в базе данных"""
    engine = create_engine(Config.DATABASE_URL or 'sqlite:///announcements.db',
                          connect_args={'timeout': 15})
    Base.metadata.create_all(engine)
