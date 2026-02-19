from fastapi import APIRouter, Depends
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas import FavoriteResponse, RecipeListItem, TagOut, UserPublic
from src.auth.deps import get_current_user, get_db_session
from src.db.models import AppUser, Favorite, Recipe

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get(
    "",
    response_model=list[RecipeListItem],
    summary="List favorite recipes",
    description="Returns recipes favorited by the current user.",
    operation_id="favorites_list",
)
async def list_favorites(
    user: AppUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[RecipeListItem]:
    """List favorited recipes for current user."""
    result = await session.execute(
        select(Recipe)
        .join(Favorite, Favorite.recipe_id == Recipe.id)
        .where(Favorite.user_id == user.id)
        .options(selectinload(Recipe.author), selectinload(Recipe.tags))
        .order_by(Favorite.created_at.desc())
    )
    recipes = result.scalars().unique().all()

    return [
        RecipeListItem(
            id=r.id,
            title=r.title,
            description=r.description,
            prep_time_minutes=r.prep_time_minutes,
            cook_time_minutes=r.cook_time_minutes,
            servings=r.servings,
            image_url=r.image_url,
            is_public=r.is_public,
            created_at=r.created_at,
            updated_at=r.updated_at,
            author=UserPublic(id=r.author.id, email=r.author.email, display_name=r.author.display_name)
            if r.author
            else None,
            tags=[TagOut(id=t.id, name=t.name) for t in r.tags],
            is_favorite=True,
        )
        for r in recipes
    ]


@router.post(
    "/{recipe_id}/toggle",
    response_model=FavoriteResponse,
    summary="Toggle favorite",
    description="Favorites/unfavorites the given recipe for the current user.",
    operation_id="favorites_toggle",
)
async def toggle_favorite(
    recipe_id: int,
    user: AppUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FavoriteResponse:
    """Toggle favorite state for a recipe."""
    res = await session.execute(
        select(Favorite).where(and_(Favorite.user_id == user.id, Favorite.recipe_id == recipe_id))
    )
    fav = res.scalar_one_or_none()
    if fav is None:
        session.add(Favorite(user_id=user.id, recipe_id=recipe_id))
        return FavoriteResponse(recipe_id=recipe_id, is_favorite=True)

    await session.execute(
        delete(Favorite).where(and_(Favorite.user_id == user.id, Favorite.recipe_id == recipe_id))
    )
    return FavoriteResponse(recipe_id=recipe_id, is_favorite=False)
