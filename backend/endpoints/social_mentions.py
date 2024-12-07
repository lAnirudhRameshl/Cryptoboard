from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from database import get_db
from models import SocialMentionChartData
from typing import List

router = APIRouter()

@router.get("/api/social-mentions", response_model=List[SocialMentionChartData])
async def get_social_mentions(db: AsyncSession = Depends(get_db)):
    biggie_query = """
        SELECT 
            top_cryptos.crypto_id AS crypto_id,
            top_cryptos.crypto_name AS crypto_name,
            top_cryptos.symbol AS symbol,
            ARRAY_AGG(
                COALESCE(daily_mentions.mentions, 0) 
                ORDER BY series.day
            ) AS mentions
        FROM 
            generate_series(
                DATE_TRUNC('day', NOW() - INTERVAL '6 days'), 
                DATE_TRUNC('day', NOW()), 
                INTERVAL '1 day'
            ) AS series(day)
        CROSS JOIN 
            (
                SELECT 
                    cryptocurrencies.crypto_id, 
                    cryptocurrencies.name AS crypto_name, 
                    cryptocurrencies.symbol
                FROM cryptocurrencies
                LIMIT 3
            ) AS top_cryptos
        LEFT JOIN (
            SELECT 
                social_mentions.crypto_id AS crypto_id, 
                DATE_TRUNC('day', social_mentions.created_at) AS day, 
                COUNT(*) AS mentions
            FROM social_mentions
            WHERE social_mentions.created_at >= NOW() - INTERVAL '7 days'
            GROUP BY social_mentions.crypto_id, DATE_TRUNC('day', social_mentions.created_at)
        ) AS daily_mentions
        ON 
            daily_mentions.crypto_id = top_cryptos.crypto_id 
            AND daily_mentions.day = series.day
        GROUP BY 
            top_cryptos.crypto_id, 
            top_cryptos.crypto_name, 
            top_cryptos.symbol;
    """

    # Execute the final query
    results = await db.execute(text(biggie_query))
    results_list = results.fetchall()

    if not results_list:
        raise HTTPException(status_code=404, detail="No social mentions found")

    return [
        {
            "crypto_id": row.crypto_id,
            "crypto_name": row.crypto_name,
            "symbol": row.symbol,
            "mentions": row.mentions,
        }
        for row in results_list
    ]
