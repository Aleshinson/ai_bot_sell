from sqlalchemy import Column, BigInteger, Integer, String, DateTime, Boolean, Text, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from config import Config
import datetime

Base = declarative_base()


class Announcement(Base):
    """Модель объявления"""
    __tablename__ = 'announcements'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    bot_name = Column(String(255), nullable=False)
    bot_function = Column(String(255), nullable=False)
    solution_description = Column(Text, nullable=False)
    included_features = Column(Text, nullable=False)
    client_requirements = Column(Text, nullable=False)
    launch_time = Column(String(50), nullable=False)  # Срок запуска
    price = Column(String(100), nullable=False)      # Цена
    complexity = Column(String(50), nullable=False)  # Сложность
    demo_url = Column(String(2048), nullable=True)  # Ссылка на демо
    documents = Column(JSON, nullable=True)  # JSON с информацией о документах
    videos = Column(JSON, nullable=True)  # JSON с информацией о видео
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


# Создание базы данных
def create_tables():
    """Создание таблиц в базе данных"""
    engine = create_engine(Config.DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
    Base.metadata.create_all(engine)
