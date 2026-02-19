from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import TagCreateRequest, TagOut
from src.auth.deps import get_db_session
from src.db.models import Tag

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get(
    "",
    response_model=list[TagOut],
    summary="List tags",
    description="List all tags.",
    operation_id="tags_list",
)
async def list_tags(session: AsyncSession = Depends(get_db_session)) -> list[TagOut]:
    """List all tags."""
    result = await session.execute(select(Tag).order_by(Tag.name.asc()))
    tags = result.scalars().all()
    return [TagOut(id=t.id, name=t.name) for t in tags]


@router.post(
    "",
    response_model=TagOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create tag",
    description="Create a new tag (name must be unique).",
    operation_id="tags_create",
)
async def create_tag(payload: TagCreateRequest, session: AsyncSession = Depends(get_db_session)) -> TagOut:
    """Create a tag."""
    existing = await session.execute(select(Tag).where(Tag.name == payload.name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Tag already exists")

    tag = Tag(name=payload.name)
    session.add(tag)
    await session.flush()
    return TagOut(id=tag.id, name=tag.name)
