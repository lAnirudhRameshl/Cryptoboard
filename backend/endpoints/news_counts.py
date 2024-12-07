from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func, text
from database import get_db
from models import Cryptocurrency, NewsMention, NewsCountResponse
from typing import List

router = APIRouter()

# Fetch news count data for the last 7 days for the top three cryptocurrencies.
@router.get("/api/news-count", response_model=List[NewsCountResponse])
async def get_news_counts(db: AsyncSession = Depends(get_db)):
    # Query for the top 3 cryptocurrencies based on news mentions in the last 7 days
    top_cryptos_subquery = (
        select(
            Cryptocurrency.crypto_id,
            Cryptocurrency.name,
            Cryptocurrency.symbol,
            func.count(NewsMention.id).label("news_count")
        )
        .join(NewsMention, Cryptocurrency.crypto_id == NewsMention.crypto_id)
        .where(NewsMention.fetch_date >= func.now() - text("INTERVAL '7 days'"))
        .group_by(Cryptocurrency.crypto_id, Cryptocurrency.name, Cryptocurrency.symbol)
        .order_by(func.count(NewsMention.id).desc())
        .limit(3)
        .subquery()
    )

    # Final query to fetch top cryptocurrencies and their news counts
    query = select(
        top_cryptos_subquery.c.crypto_id.label("crypto_id"),
        top_cryptos_subquery.c.name.label("crypto_name"),
        top_cryptos_subquery.c.symbol.label("symbol"),
        top_cryptos_subquery.c.news_count
    )

    results = await db.execute(query)
    results_list = results.fetchall()

    if not results_list:
        raise HTTPException(status_code=404, detail="No news counts found")

    return [
        {
            "crypto_id": row.crypto_id,
            "crypto_name": row.crypto_name,
            "symbol": row.symbol,
            "news_count": row.news_count
        }
        for row in results_list
    ]