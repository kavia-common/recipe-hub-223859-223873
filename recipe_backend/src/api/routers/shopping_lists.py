from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas import (
    ShoppingListCreateRequest,
    ShoppingListItemOut,
    ShoppingListOut,
    ShoppingListUpdateRequest,
)
from src.auth.deps import get_current_user, get_db_session
from src.db.models import AppUser, ShoppingList, ShoppingListItem

router = APIRouter(prefix="/shopping-lists", tags=["shopping-lists"])


@router.get(
    "",
    response_model=list[ShoppingListOut],
    summary="List shopping lists",
    description="List shopping lists owned by the current user.",
    operation_id="shopping_lists_list",
)
async def list_lists(
    user: AppUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ShoppingListOut]:
    """List shopping lists for current user."""
    result = await session.execute(
        select(ShoppingList)
        .where(ShoppingList.user_id == user.id)
        .options(selectinload(ShoppingList.items))
        .order_by(ShoppingList.updated_at.desc())
    )
    lists = result.scalars().unique().all()

    return [
        ShoppingListOut(
            id=sl.id,
            name=sl.name,
            created_at=sl.created_at,
            updated_at=sl.updated_at,
            items=[
                ShoppingListItemOut(
                    id=i.id,
                    position=i.position,
                    item_name=i.item_name,
                    quantity=i.quantity,
                    unit=i.unit,
                    notes=i.notes,
                    is_checked=i.is_checked,
                    source_recipe_id=i.source_recipe_id,
                )
                for i in sorted(sl.items, key=lambda x: x.position)
            ],
        )
        for sl in lists
    ]


@router.post(
    "",
    response_model=ShoppingListOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create shopping list",
    description="Create a shopping list for the current user.",
    operation_id="shopping_lists_create",
)
async def create_list(
    payload: ShoppingListCreateRequest,
    user: AppUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ShoppingListOut:
    """Create a shopping list."""
    sl = ShoppingList(user_id=user.id, name=payload.name)
    session.add(sl)
    await session.flush()
    return ShoppingListOut(id=sl.id, name=sl.name, created_at=sl.created_at, updated_at=sl.updated_at, items=[])


@router.get(
    "/{list_id}",
    response_model=ShoppingListOut,
    summary="Get shopping list",
    description="Get a shopping list with its items.",
    operation_id="shopping_lists_get",
)
async def get_list(
    list_id: int,
    user: AppUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ShoppingListOut:
    """Get a shopping list detail."""
    result = await session.execute(
        select(ShoppingList)
        .where(ShoppingList.id == list_id, ShoppingList.user_id == user.id)
        .options(selectinload(ShoppingList.items))
    )
    sl = result.scalar_one_or_none()
    if sl is None:
        raise HTTPException(status_code=404, detail="Shopping list not found")

    return ShoppingListOut(
        id=sl.id,
        name=sl.name,
        created_at=sl.created_at,
        updated_at=sl.updated_at,
        items=[
            ShoppingListItemOut(
                id=i.id,
                position=i.position,
                item_name=i.item_name,
                quantity=i.quantity,
                unit=i.unit,
                notes=i.notes,
                is_checked=i.is_checked,
                source_recipe_id=i.source_recipe_id,
            )
            for i in sorted(sl.items, key=lambda x: x.position)
        ],
    )


@router.put(
    "/{list_id}",
    response_model=ShoppingListOut,
    summary="Update shopping list",
    description="Update list name and/or replace its items.",
    operation_id="shopping_lists_update",
)
async def update_list(
    list_id: int,
    payload: ShoppingListUpdateRequest,
    user: AppUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ShoppingListOut:
    """Update list name and/or items."""
    result = await session.execute(
        select(ShoppingList)
        .where(ShoppingList.id == list_id, ShoppingList.user_id == user.id)
        .options(selectinload(ShoppingList.items))
    )
    sl = result.scalar_one_or_none()
    if sl is None:
        raise HTTPException(status_code=404, detail="Shopping list not found")

    if payload.name is not None:
        sl.name = payload.name

    if payload.items is not None:
        await session.execute(delete(ShoppingListItem).where(ShoppingListItem.shopping_list_id == sl.id))
        await session.flush()
        for it in payload.items:
            session.add(
                ShoppingListItem(
                    shopping_list_id=sl.id,
                    position=it.position,
                    item_name=it.item_name,
                    quantity=it.quantity,
                    unit=it.unit,
                    notes=it.notes,
                    is_checked=it.is_checked,
                    source_recipe_id=it.source_recipe_id,
                )
            )

    sl.updated_at = datetime.now(timezone.utc)
    await session.flush()

    return await get_list(sl.id, user=user, session=session)


@router.delete(
    "/{list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete shopping list",
    description="Delete a shopping list.",
    operation_id="shopping_lists_delete",
)
async def delete_list(
    list_id: int,
    user: AppUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a shopping list."""
    res = await session.execute(select(ShoppingList).where(ShoppingList.id == list_id, ShoppingList.user_id == user.id))
    sl = res.scalar_one_or_none()
    if sl is None:
        raise HTTPException(status_code=404, detail="Shopping list not found")

    await session.execute(delete(ShoppingList).where(ShoppingList.id == sl.id))
    return None
