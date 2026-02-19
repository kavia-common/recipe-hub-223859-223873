from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class UserPublic(BaseModel):
    id: int = Field(..., description="User id")
    email: str = Field(..., description="User email")
    display_name: Optional[str] = Field(None, description="Display name")


class AuthRegisterRequest(BaseModel):
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=6, description="Plaintext password (min 6 chars)")
    display_name: Optional[str] = Field(None, description="Display name")


class AuthLoginRequest(BaseModel):
    email: str = Field(..., description="Email address")
    password: str = Field(..., description="Plaintext password")


class AuthTokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    user: UserPublic = Field(..., description="Authenticated user")


class RecipeIngredientIn(BaseModel):
    position: int = Field(0, description="Ingredient ordering position")
    name: str = Field(..., description="Ingredient name")
    quantity: Optional[str] = Field(None, description="Quantity (free-form)")
    unit: Optional[str] = Field(None, description="Unit (free-form)")
    notes: Optional[str] = Field(None, description="Notes")


class RecipeIngredientOut(RecipeIngredientIn):
    id: int = Field(..., description="Ingredient id")


class RecipeStepIn(BaseModel):
    step_number: int = Field(..., description="Step number (1-based)")
    instruction: str = Field(..., description="Instruction text")


class RecipeStepOut(RecipeStepIn):
    id: int = Field(..., description="Step id")


class TagOut(BaseModel):
    id: int = Field(..., description="Tag id")
    name: str = Field(..., description="Tag name")


class RecipeBase(BaseModel):
    title: str = Field(..., description="Recipe title")
    description: Optional[str] = Field(None, description="Recipe description")
    prep_time_minutes: int = Field(0, ge=0, description="Preparation time in minutes")
    cook_time_minutes: int = Field(0, ge=0, description="Cook time in minutes")
    servings: int = Field(1, ge=1, description="Number of servings")
    image_url: Optional[str] = Field(None, description="Image URL")
    is_public: bool = Field(True, description="Whether recipe is publicly visible")


class RecipeCreateRequest(RecipeBase):
    ingredients: List[RecipeIngredientIn] = Field(default_factory=list, description="Ingredients list")
    steps: List[RecipeStepIn] = Field(default_factory=list, description="Steps list")
    tag_names: List[str] = Field(default_factory=list, description="List of tag names")


class RecipeUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, description="Recipe title")
    description: Optional[str] = Field(None, description="Recipe description")
    prep_time_minutes: Optional[int] = Field(None, ge=0, description="Preparation time in minutes")
    cook_time_minutes: Optional[int] = Field(None, ge=0, description="Cook time in minutes")
    servings: Optional[int] = Field(None, ge=1, description="Servings")
    image_url: Optional[str] = Field(None, description="Image URL")
    is_public: Optional[bool] = Field(None, description="Public visibility")
    ingredients: Optional[List[RecipeIngredientIn]] = Field(None, description="Replace ingredients list")
    steps: Optional[List[RecipeStepIn]] = Field(None, description="Replace steps list")
    tag_names: Optional[List[str]] = Field(None, description="Replace tag names list")


class RecipeListItem(BaseModel):
    id: int = Field(..., description="Recipe id")
    title: str = Field(..., description="Title")
    description: Optional[str] = Field(None, description="Description")
    prep_time_minutes: int = Field(..., description="Prep time")
    cook_time_minutes: int = Field(..., description="Cook time")
    servings: int = Field(..., description="Servings")
    image_url: Optional[str] = Field(None, description="Image URL")
    is_public: bool = Field(..., description="Public visibility")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")
    author: Optional[UserPublic] = Field(None, description="Author")
    tags: List[TagOut] = Field(default_factory=list, description="Tags")
    is_favorite: bool = Field(False, description="Whether current user has favorited")


class RecipeDetail(RecipeListItem):
    ingredients: List[RecipeIngredientOut] = Field(default_factory=list, description="Ingredients")
    steps: List[RecipeStepOut] = Field(default_factory=list, description="Steps")


class ShoppingListItemIn(BaseModel):
    position: int = Field(0, description="Ordering position")
    item_name: str = Field(..., description="Item name")
    quantity: Optional[str] = Field(None, description="Quantity")
    unit: Optional[str] = Field(None, description="Unit")
    notes: Optional[str] = Field(None, description="Notes")
    is_checked: bool = Field(False, description="Checked status")
    source_recipe_id: Optional[int] = Field(None, description="Optional source recipe id")


class ShoppingListItemOut(ShoppingListItemIn):
    id: int = Field(..., description="Item id")


class ShoppingListOut(BaseModel):
    id: int = Field(..., description="Shopping list id")
    name: str = Field(..., description="List name")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")
    items: List[ShoppingListItemOut] = Field(default_factory=list, description="Items")


class ShoppingListCreateRequest(BaseModel):
    name: str = Field(..., description="List name")


class ShoppingListUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Updated list name")
    items: Optional[List[ShoppingListItemIn]] = Field(None, description="Replace items list")


class FavoriteResponse(BaseModel):
    recipe_id: int = Field(..., description="Recipe id")
    is_favorite: bool = Field(..., description="Favorite state")


class TagCreateRequest(BaseModel):
    name: str = Field(..., description="Tag name")
