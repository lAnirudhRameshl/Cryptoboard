from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
from models import SocialMention, TopPostResponse

router = APIRouter()

# Fetch the top Reddit post about cryptocurrencies based on its score.
@router.get("/api/top-post", response_model=TopPostResponse)
async def get_top_post(db: AsyncSession = Depends(get_db)):
    # Query to fetch the top post based on the highest score
    query = (
        select(SocialMention.id, SocialMention.url)
        .where(SocialMention.is_post == True)
        .order_by(SocialMention.score.desc())
        .limit(1)
    )

    result = await db.execute(query)
    top_post = result.fetchone()

    if not top_post:
        raise HTTPException(status_code=404, detail="No posts found")

    return {
        "id": top_post.id,
        "url": top_post.url
    }

