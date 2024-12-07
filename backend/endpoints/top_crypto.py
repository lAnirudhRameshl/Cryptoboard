from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func, text
from database import get_db
from models import Cryptocurrency, SocialMention, TopCryptoResponse
from typing import List

router = APIRouter()

@router.get("/api/top-crypto", response_model=List[TopCryptoResponse])
async def get_top_crypto(db: AsyncSession = Depends(get_db)):
    # Subquery for mentions from the last day
    last_day_mentions = (
        select(
            SocialMention.crypto_id,
            func.sum(SocialMention.score).label("last_day_mentions")
        )
        .where(SocialMention.fetch_date >= func.now() - text("INTERVAL '1 day'"))
        .group_by(SocialMention.crypto_id)
        .subquery()
    )

    # Subquery for mentions from the previous day
    previous_day_mentions = (
        select(
            SocialMention.crypto_id,
            func.sum(SocialMention.score).label("previous_day_mentions")
        )
        .where(
            SocialMention.fetch_date.between(
                func.now() - text("INTERVAL '2 days'"),
                func.now() - text("INTERVAL '1 day'")
            )
        )
        .group_by(SocialMention.crypto_id)
        .subquery()
    )

    # Query to calculate percentage change in mentions
    query = (
        select(
            Cryptocurrency.crypto_id.label("crypto_id"),
            Cryptocurrency.name.label("crypto_name"),
            Cryptocurrency.symbol,
            func.coalesce(
                (
                    (last_day_mentions.c.last_day_mentions - previous_day_mentions.c.previous_day_mentions)
                    * 100.0
                    / func.nullif(previous_day_mentions.c.previous_day_mentions, 0)
                ),
                0
            ).label("change")
        )
        .outerjoin(last_day_mentions, Cryptocurrency.crypto_id == last_day_mentions.c.crypto_id)
        .outerjoin(previous_day_mentions, Cryptocurrency.crypto_id == previous_day_mentions.c.crypto_id)
        .order_by(func.coalesce(
            (
                (last_day_mentions.c.last_day_mentions - previous_day_mentions.c.previous_day_mentions)
                * 100.0
                / func.nullif(previous_day_mentions.c.previous_day_mentions, 0)
            ),
            0
        ).desc())
        .limit(3)
    )

    results = await db.execute(query)
    results_list = results.fetchall()

    if not results_list:
        raise HTTPException(status_code=404, detail="No data found")

    return [
        {
            "crypto_id": row.crypto_id,
            "crypto_name": row.crypto_name,
            "symbol": row.symbol,
            "change": row.change
        }
        for row in results_list
    ]
