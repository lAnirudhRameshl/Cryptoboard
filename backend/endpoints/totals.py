# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from sqlalchemy.sql import func
# from database import get_db
# from models import TotalsResponse, NewsMention, SocialMention

# router = APIRouter()

# # Fetch the total counts of news articles and social media posts within the last 24 hours.
# @router.get("/api/totals/time_window=24", response_model=TotalsResponse)
# async def get_totals(db: AsyncSession = Depends(get_db)):
#     # Subquery for news count
#     news_count_query = (
#         select(func.count(NewsMention.id).label("news_count"))
#         .where(NewsMention.fetch_date >= func.now() - func.interval("24 hours"))
#     )

#     # Subquery for social count
#     social_count_query = (
#         select(func.count(SocialMention.id).label("social_count"))
#         .where(SocialMention.fetch_date >= func.now() - func.interval("24 hours"))
#     )

#     news_result = await db.execute(news_count_query)
#     social_result = await db.execute(social_count_query)

#     # Fetch counts
#     news_count = news_result.scalar()
#     social_count = social_result.scalar()

#     if news_count is None or social_count is None:
#         raise HTTPException(status_code=404, detail="No data found for the time window")

#     return {
#         "news_count": news_count,
#         "social_count": social_count
#     }

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select, func, text
from database import get_db

router = APIRouter()

@router.get("/api/totals")
async def get_totals(db: AsyncSession = Depends(get_db)):
    # News count query
    news_count_query = (
        select(func.count().label("news_count"))
        .select_from(text("news_mentions"))
        .where(text("fetch_date >= now() - interval '24 hours'"))
    )

    # Execute the query
    news_result = await db.execute(news_count_query)
    news_count = news_result.scalar() or 0

    # Social count query (similar structure)
    social_count_query = (
        select(func.count().label("social_count"))
        .select_from(text("social_mentions"))
        .where(text("fetch_date >= now() - interval '24 hours'"))
    )

    social_result = await db.execute(social_count_query)
    social_count = social_result.scalar() or 0

    return {"news_count": news_count, "social_count": social_count}
