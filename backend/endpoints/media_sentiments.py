
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func, case, text
from database import get_db
from models import Cryptocurrency, NewsMention, SocialMention, MediaSentimentResponse
from typing import List

router = APIRouter()

@router.get("/api/media-sentiments", response_model=List[MediaSentimentResponse])
async def get_media_sentiments(db: AsyncSession = Depends(get_db)):
    interval = "24 hours"

    # Subquery for top cryptocurrencies based on news and social mentions
    top_cryptos_subquery = (
        select(
            Cryptocurrency.crypto_id,
            Cryptocurrency.name,
            Cryptocurrency.symbol,
            func.count(NewsMention.id + SocialMention.id).label("mention_count"),
        )
        .outerjoin(NewsMention, Cryptocurrency.crypto_id == NewsMention.crypto_id)
        .outerjoin(SocialMention, Cryptocurrency.crypto_id == SocialMention.crypto_id)
        .where(
            func.greatest(
                func.coalesce(NewsMention.fetch_date, func.now() - text(f"INTERVAL '{interval}'")),
                func.coalesce(SocialMention.fetch_date, func.now() - text(f"INTERVAL '{interval}'"))
            ) >= func.now() - text(f"INTERVAL '{interval}'")
        )
        .group_by(Cryptocurrency.crypto_id, Cryptocurrency.name, Cryptocurrency.symbol)
        .order_by(func.count(NewsMention.id + SocialMention.id).desc())
        .limit(3)
        .subquery()
    )

    # Main query to get sentiment counts
    query = (
        select(
            top_cryptos_subquery.c.crypto_id.label("crypto_id"),
            top_cryptos_subquery.c.name.label("crypto_name"),
            top_cryptos_subquery.c.symbol,
            func.sum(case((NewsMention.sentiment_score >= 0, 1), else_=0)).label("positive_news_sentiment_count"),
            func.sum(case((NewsMention.sentiment_score < 0, 1), else_=0)).label("negative_news_sentiment_count"),
            func.sum(case((SocialMention.sentiment_score >= 0, 1), else_=0)).label("positive_social_sentiment_count"),
            func.sum(case((SocialMention.sentiment_score < 0, 1), else_=0)).label("negative_social_sentiment_count"),
        )
        .join(NewsMention, NewsMention.crypto_id == top_cryptos_subquery.c.crypto_id, isouter=True)
        .join(SocialMention, SocialMention.crypto_id == top_cryptos_subquery.c.crypto_id, isouter=True)
        .group_by(
            top_cryptos_subquery.c.crypto_id,
            top_cryptos_subquery.c.name,
            top_cryptos_subquery.c.symbol
        )
    )

    results = await db.execute(query)
    results_list = results.fetchall()

    if not results_list:
        raise HTTPException(status_code=404, detail="No media sentiment data found")

    return [
        {
            "crypto_id": row.crypto_id,
            "crypto_name": row.crypto_name,
            "symbol": row.symbol,
            "positive_news_sentiment_count": row.positive_news_sentiment_count,
            "negative_news_sentiment_count": row.negative_news_sentiment_count,
            "positive_social_sentiment_count": row.positive_social_sentiment_count,
            "negative_social_sentiment_count": row.negative_social_sentiment_count,
        }
        for row in results_list
    ]
