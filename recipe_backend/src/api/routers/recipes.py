from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas import (
    RecipeCreateRequest,
    RecipeDetail,
    RecipeIngredientOut,
    RecipeListItem,
    RecipeStepOut,
    RecipeUpdateRequest,
    TagOut,
    UserPublic,
)
from src.auth.deps import get_current_user, get_db_session
from src.db.models import AppUser, Favorite, Recipe, RecipeIngredient, RecipeStep, Tag

router = APIRouter(prefix="/recipes", tags=["recipes"])


async def _is_favorite(session: AsyncSession, user_id: int, recipe_id: int) -> bool:
    res = await session.execute(
        select(Favorite).where(and_(Favorite.user_id == user_id, Favorite.recipe_id == recipe_id))
    )
    return res.scalar_one_or_none() is not None


def _to_user_public(user: Optional[AppUser]) -> Optional[UserPublic]:
    if user is None:
        return None
    return UserPublic(id=user.id, email=user.email, display_name=user.display_name)


@router.get(
    "",
    response_model=list[RecipeListItem],
    summary="List recipes",
    description="List public recipes; if authenticated, includes favorite state and can include your private recipes.",
    operation_id="recipes_list",
)
async def list_recipes(
    q: Optional[str] = Query(None, description="Search query for title/description"),
    tag: Optional[str] = Query(None, description="Filter by tag name"),
    mine: bool = Query(False, description="If true, return only recipes authored by current user (requires auth)"),
    session: AsyncSession = Depends(get_db_session),
    user: Optional[AppUser] = Depends(get_current_user),
) -> list[RecipeListItem]:
    """List/search recipes."""
    stmt = (
        select(Recipe)
        .options(selectinload(Recipe.author), selectinload(Recipe.tags))
        .order_by(Recipe.updated_at.desc())
    )

    conditions = []
    if q:
        like = f"%{q}%"
        conditions.append(or_(Recipe.title.ilike(like), Recipe.description.ilike(like)))
    if tag:
        stmt = stmt.join(Recipe.tags).where(Tag.name == tag)
    if mine:
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        conditions.append(Recipe.author_user_id == user.id)
    else:
        # public recipes always visible; include own private recipes if logged in
        if user is None:
            conditions.append(Recipe.is_public.is_(True))
        else:
            conditions.append(or_(Recipe.is_public.is_(True), Recipe.author_user_id == user.id))

    if conditions:
        stmt = stmt.where(and_(*conditions))

    result = await session.execute(stmt)
    recipes = result.scalars().unique().all()

    items: list[RecipeListItem] = []
    for r in recipes:
        fav = False
        if user is not None:
            fav = await _is_favorite(session, user.id, r.id)
        items.append(
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
                author=_to_user_public(r.author),
                tags=[TagOut(id=t.id, name=t.name) for t in r.tags],
                is_favorite=fav,
            )
        )
    return items


@router.get(
    "/{recipe_id}",
    response_model=RecipeDetail,
    summary="Get recipe detail",
    description="Get a recipe including ingredients, steps, tags. Private recipes visible only to the author.",
    operation_id="recipes_get",
)
async def get_recipe(
    recipe_id: int,
    session: AsyncSession = Depends(get_db_session),
    user: Optional[AppUser] = Depends(get_current_user),
) -> RecipeDetail:
    """Get recipe detail."""
    result = await session.execute(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(
            selectinload(Recipe.author),
            selectinload(Recipe.tags),
            selectinload(Recipe.ingredients),
            selectinload(Recipe.steps),
        )
    )
    recipe = result.scalar_one_or_none()
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    if not recipe.is_public:
        if user is None or recipe.author_user_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")

    fav = False
    if user is not None:
        fav = await _is_favorite(session, user.id, recipe.id)

    return RecipeDetail(
        id=recipe.id,
        title=recipe.title,
        description=recipe.description,
        prep_time_minutes=recipe.prep_time_minutes,
        cook_time_minutes=recipe.cook_time_minutes,
        servings=recipe.servings,
        image_url=recipe.image_url,
        is_public=recipe.is_public,
        created_at=recipe.created_at,
        updated_at=recipe.updated_at,
        author=_to_user_public(recipe.author),
        tags=[TagOut(id=t.id, name=t.name) for t in recipe.tags],
        is_favorite=fav,
        ingredients=[
            RecipeIngredientOut(
                id=i.id,
                position=i.position,
                name=i.name,
                quantity=i.quantity,
                unit=i.unit,
                notes=i.notes,
            )
            for i in sorted(recipe.ingredients, key=lambda x: x.position)
        ],
        steps=[
            RecipeStepOut(id=s.id, step_number=s.step_number, instruction=s.instruction)
            for s in sorted(recipe.steps, key=lambda x: x.step_number)
        ],
    )


@router.post(
    "",
    response_model=RecipeDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create recipe",
    description="Create a recipe owned by the current user.",
    operation_id="recipes_create",
)
async def create_recipe(
    payload: RecipeCreateRequest,
    user: AppUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> RecipeDetail:
    """Create a new recipe."""
    recipe = Recipe(
        author_user_id=user.id,
        title=payload.title,
        description=payload.description,
        prep_time_minutes=payload.prep_time_minutes,
        cook_time_minutes=payload.cook_time_minutes,
        servings=payload.servings,
        image_url=payload.image_url,
        is_public=payload.is_public,
    )
    session.add(recipe)
    await session.flush()

    # Ingredients
    for ing in payload.ingredients:
        session.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                position=ing.position,
                name=ing.name,
                quantity=ing.quantity,
                unit=ing.unit,
                notes=ing.notes,
            )
        )

    # Steps
    for st in payload.steps:
        session.add(RecipeStep(recipe_id=recipe.id, step_number=st.step_number, instruction=st.instruction))

    # Tags
    tags: list[Tag] = []
    for name in payload.tag_names:
        name_norm = name.strip()
        if not name_norm:
            continue
        res = await session.execute(select(Tag).where(func.lower(Tag.name) == name_norm.lower()))
        t = res.scalar_one_or_none()
        if t is None:
            t = Tag(name=name_norm)
            session.add(t)
            await session.flush()
        tags.append(t)
    recipe.tags = tags

    # Reload
    return await get_recipe(recipe.id, session=session, user=user)


@router.put(
    "/{recipe_id}",
    response_model=RecipeDetail,
    summary="Update recipe",
    description="Update a recipe owned by the current user.",
    operation_id="recipes_update",
)
async def update_recipe(
    recipe_id: int,
    payload: RecipeUpdateRequest,
    user: AppUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> RecipeDetail:
    """Update an existing recipe."""
    result = await session.execute(
        select(Recipe)
        .where(Recipe.id == recipe_id)
        .options(selectinload(Recipe.tags), selectinload(Recipe.ingredients), selectinload(Recipe.steps))
    )
    recipe = result.scalar_one_or_none()
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if recipe.author_user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    for field in ["title", "description", "prep_time_minutes", "cook_time_minutes", "servings", "image_url", "is_public"]:
        val = getattr(payload, field)
        if val is not None:
            setattr(recipe, field, val)

    if payload.ingredients is not None:
        # Replace ingredients
        await session.execute(delete(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id))
        await session.flush()
        for ing in payload.ingredients:
            session.add(
                RecipeIngredient(
                    recipe_id=recipe.id,
                    position=ing.position,
                    name=ing.name,
                    quantity=ing.quantity,
                    unit=ing.unit,
                    notes=ing.notes,
                )
            )

    if payload.steps is not None:
        await session.execute(delete(RecipeStep).where(RecipeStep.recipe_id == recipe.id))
        await session.flush()
        for st in payload.steps:
            session.add(RecipeStep(recipe_id=recipe.id, step_number=st.step_number, instruction=st.instruction))

    if payload.tag_names is not None:
        tags: list[Tag] = []
        for name in payload.tag_names:
            name_norm = name.strip()
            if not name_norm:
                continue
            res = await session.execute(select(Tag).where(func.lower(Tag.name) == name_norm.lower()))
            t = res.scalar_one_or_none()
            if t is None:
                t = Tag(name=name_norm)
                session.add(t)
                await session.flush()
            tags.append(t)
        recipe.tags = tags

    return await get_recipe(recipe.id, session=session, user=user)


@router.delete(
    "/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete recipe",
    description="Delete a recipe owned by the current user.",
    operation_id="recipes_delete",
)
async def delete_recipe(
    recipe_id: int,
    user: AppUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a recipe."""
    result = await session.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if recipe.author_user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    await session.execute(delete(Recipe).where(Recipe.id == recipe_id))
    return None
