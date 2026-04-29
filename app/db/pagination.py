from math import ceil
from typing import Any
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession


async def paginate(
    db: AsyncSession,
    query: Select,
    count_query: Select,
    page: int,
    limit: int,
) -> dict[str, Any]:
    offset = (page - 1) * limit
    total = (await db.execute(count_query)).scalar() or 0
    items = (await db.execute(query.offset(offset).limit(limit))).scalars().all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": ceil(total / limit) if total > 0 else 1,
    }
