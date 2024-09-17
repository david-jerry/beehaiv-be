from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.db.db import init_db
from src.utils.logger import LOGGER
from .errors import register_all_errors
from .middleware import register_middleware

from src.app.auth.views import auth_router, user_router
from src.app.transactions.views import transaction_router

version = "v1"

description = """
A REST API for BeeHaiv Financial services.

This REST API is able to;
- Create Read Update And delete transaction records
- Create Read Update and Delete Blog Post with addition to category
- View Transaction History
- Create Business Accounts
- Apply for Loans, Mortgage Loans and Startup Loans for Businesses
    """

version_prefix =f"/api/{version}"

@asynccontextmanager
async def life_span(app: FastAPI):
    LOGGER.info("Server is running")
    await init_db()
    yield
    LOGGER.info("Server has stopped")

app = FastAPI(
    title="BeeHaiv Financial Tracker",
    description=description,
    version=version,
    lifespan=life_span,
    license_info={"name": "MIT License", "url": "https://github.com/jerry-david/beehaiv-be/LICENSE"},
    contact={
        "name": "Jeremiah David",
        "url": "https://github.com/jerry-david",
        "email": "jeremiahedavid@gmail.com",
    },
    terms_of_service="https://github.com/jerry-david/beehaiv-be/TERMS.md",
    openapi_url=f"{version_prefix}/openapi.json",
    docs_url=f"{version_prefix}/docs",
    redoc_url=f"{version_prefix}/redocs"
)

register_all_errors(app)

register_middleware(app)


# app.include_router(book_router, prefix=f"{version_prefix}/books", tags=["books"])
app.include_router(auth_router, prefix=f"{version_prefix}/auth", tags=["auth"])
app.include_router(user_router, prefix=f"{version_prefix}/users", tags=["users"])
app.include_router(transaction_router, prefix=f"{version_prefix}/transactions", tags=["transaction"])
# app.include_router(review_router, prefix=f"{version_prefix}/reviews", tags=["reviews"])
# app.include_router(tags_router, prefix=f"{version_prefix}/tags", tags=["tags"])
