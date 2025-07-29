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
    task_solution = Column(Text, nullable=False)
    included_features = Column(Text, nullable=False)
    client_requirements = Column(Text, nullable=False)
    launch_time = Column(String(50), nullable=False)
    price = Column(String(100), nullable=False)
    complexity = Column(Text, nullable=False)
    demo_url = Column(String(2048), nullable=True)
    documents = Column(JSON, nullable=True)
    videos = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_approved = Column(Boolean, default=None)
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


class CustomRequest(Base):
    """Модель заявки на индивидуальное решение"""
    __tablename__ = 'custom_requests'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    business_description = Column(Text, nullable=False)
    automation_task = Column(Text, nullable=False)
    budget = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_approved = Column(Boolean, default=None)
    moderator_id = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<CustomRequest(id={self.id}, user_id={self.user_id}, is_approved={self.is_approved})>"

    @property
    def status_text(self) -> str:
        """Текстовое представление статуса"""
        if self.is_approved is None:
            return "На модерации"
        elif self.is_approved:
            return "Одобрена"
        else:
            return "Отклонена"

    def is_pending(self) -> bool:
        """Проверка, находится ли заявка на модерации"""
        return self.is_approved is None

    def is_approved_status(self) -> bool:
        """Проверка, одобрена ли заявка"""
        return self.is_approved is True

    def is_rejected(self) -> bool:
        """Проверка, отклонена ли заявка"""
        return self.is_approved is False


# Создание базы данных
def create_tables():
    """Создание таблиц в базе данных"""
    engine = create_engine(Config.DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
    Base.metadata.create_all(engine)
