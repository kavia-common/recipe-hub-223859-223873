from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers.auth import router as auth_router
from src.api.routers.favorites import router as favorites_router
from src.api.routers.recipes import router as recipes_router
from src.api.routers.shopping_lists import router as shopping_lists_router
from src.api.routers.tags import router as tags_router

openapi_tags = [
    {"name": "system", "description": "Service health and metadata."},
    {"name": "auth", "description": "User registration, login, and session endpoints."},
    {"name": "recipes", "description": "Recipe browsing, search, and CRUD."},
    {"name": "tags", "description": "Tag listing and creation."},
    {"name": "favorites", "description": "Favorite recipes management."},
    {"name": "shopping-lists", "description": "Shopping list CRUD and items management."},
]

app = FastAPI(
    title="Recipe Hub API",
    description=(
        "Backend API for Recipe Hub.\n\n"
        "Environment variables required:\n"
        "- POSTGRES_URL (preferred) or POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_DB/POSTGRES_PORT\n"
        "- JWT_SECRET\n"
        "- JWT_EXPIRES_MINUTES (optional)\n"
    ),
    version="0.1.0",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["system"], summary="Health check", operation_id="health_check")
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}


app.include_router(auth_router)
app.include_router(recipes_router)
app.include_router(tags_router)
app.include_router(favorites_router)
app.include_router(shopping_lists_router)
