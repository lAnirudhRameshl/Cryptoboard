from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func, case, text
from database import get_db
from models import Cryptocurrency, NewsMention, SocialMention, SummaryDataResponse
from typing import List

router = APIRouter()

# Fetch metadata for the summary page by aggregating data for all cryptocurrencies.
@router.get("/api/summary-data", response_model=List[SummaryDataResponse])
async def get_summary_data(db: AsyncSession = Depends(get_db)):
    query = (
        select(
            Cryptocurrency.crypto_id.label("crypto_id"),
            Cryptocurrency.name.label("crypto_name"),
            Cryptocurrency.symbol.label("symbol"),
            func.coalesce(
                (
                    (
                        func.sum(
                            case(
                                (SocialMention.fetch_date >= func.now() - text("INTERVAL '1 day'"), 1),
                                else_=0
                            )
                        )
                        - func.sum(
                            case(
                                (
                                    SocialMention.fetch_date.between(
                                        func.now() - text("INTERVAL '2 days'"),
                                        func.now() - text("INTERVAL '1 day'"),
                                    ),
                                    1
                                ),
                                else_=0
                            )
                        )
                    ) * 100.0 /
                    func.nullif(
                        func.sum(
                            case(
                                (
                                    SocialMention.fetch_date.between(
                                        func.now() - text("INTERVAL '2 days'"),
                                        func.now() - text("INTERVAL '1 day'"),
                                    ),
                                    1
                                ),
                                else_=0
                            )
                        ),
                        0
                    )
                ),
                0
            ).label("change"),
            func.count(SocialMention.id).label("social_count"),
            func.count(NewsMention.id).label("news_count"),
            case(
                (func.avg(SocialMention.sentiment_score) >= 0, 1),
                (func.avg(SocialMention.sentiment_score) < 0, 0),
            ).label("social_sentiment_score"),  
            case(
                (func.avg(NewsMention.sentiment_score) >= 0, 1),
                (func.avg(NewsMention.sentiment_score) < 0, 0),
            ).label("news_sentiment_score"),  
        )
        .outerjoin(SocialMention, Cryptocurrency.crypto_id == SocialMention.crypto_id)
        .outerjoin(NewsMention, Cryptocurrency.crypto_id == NewsMention.crypto_id)
        .group_by(Cryptocurrency.crypto_id, Cryptocurrency.name, Cryptocurrency.symbol)
        .order_by(Cryptocurrency.name.asc())
    )

    # Execute the query
    result = await db.execute(query)
    rows = result.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No summary data found")

    return [
        {
            "crypto_id": row.crypto_id,
            "crypto_name": row.crypto_name,
            "symbol": row.symbol,
            "change": row.change,
            "social_count": row.social_count,
            "news_count": row.news_count,
            "social_sentiment_score": row.social_sentiment_score,
            "news_sentiment_score": row.news_sentiment_score,
        }
        for row in rows
    ]