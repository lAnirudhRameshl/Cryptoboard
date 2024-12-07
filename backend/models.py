


from typing import List, Optional
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Numeric
from sqlalchemy.orm import declarative_base, relationship
from pydantic import BaseModel

# SQLAlchemy Base
Base = declarative_base()

# SQLAlchemy Models
class Cryptocurrency(Base):
    __tablename__ = "cryptocurrencies"
    crypto_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)

    news_mentions = relationship("NewsMention", back_populates="cryptocurrency")
    social_mentions = relationship("SocialMention", back_populates="cryptocurrency")


class NewsMention(Base):
    __tablename__ = "news_mentions"
    id = Column(Integer, primary_key=True, index=True)
    crypto_id = Column(Integer, ForeignKey("cryptocurrencies.crypto_id"), nullable=False)
    fetch_date = Column(DateTime, nullable=False)
    sentiment_score = Column(Numeric(precision=10, scale=2), nullable=False)  # Updated

    cryptocurrency = relationship("Cryptocurrency", back_populates="news_mentions")


class SocialMention(Base):
    __tablename__ = "social_mentions"
    id = Column(Integer, primary_key=True, index=True)
    crypto_id = Column(Integer, ForeignKey("cryptocurrencies.crypto_id"), nullable=False)
    fetch_date = Column(DateTime, nullable=False)
    score = Column(Integer, nullable=False)
    is_post = Column(Boolean, default=False)
    url = Column(String, nullable=False)
    sentiment_score = Column(Numeric(precision=10, scale=2), nullable=False)  # Updated

    cryptocurrency = relationship("Cryptocurrency", back_populates="social_mentions")

# Pydantic Models
class NewsCountResponse(BaseModel):
    crypto_id: int
    crypto_name: str
    symbol: str
    news_count: int

    class Config:
        orm_mode = True


class SocialMentionChartData(BaseModel):
    crypto_id: int
    crypto_name: str
    symbol: str
    mentions: List[int]

    class Config:
        orm_mode = True


class TopCryptoResponse(BaseModel):
    crypto_id: int
    crypto_name: str
    symbol: str
    change: float

    class Config:
        orm_mode = True


class TopPostResponse(BaseModel):
    id: int
    url: str

    class Config:
        orm_mode = True


class TotalsResponse(BaseModel):
    news_count: int
    social_count: int

    class Config:
        orm_mode = True


class MediaSentimentResponse(BaseModel):
    crypto_id: int
    crypto_name: str
    symbol: str
    positive_news_sentiment_count: int
    negative_news_sentiment_count: int
    positive_social_sentiment_count: int
    negative_social_sentiment_count: int

    class Config:
        orm_mode = True


class SummaryDataResponse(BaseModel):
    crypto_id: int
    crypto_name: str
    symbol: str
    change: Optional[float]
    social_count: int
    news_count: int
    social_sentiment_score: Optional[float]
    news_sentiment_score: Optional[float]

    class Config:
        orm_mode = True
