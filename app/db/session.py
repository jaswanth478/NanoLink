from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import ssl

from config.settings import get_settings

settings = get_settings()

# Parse URL and handle SSL for asyncpg (which doesn't support sslmode in URL)
db_url = settings.database_url
connect_args = {}

if "?sslmode=require" in db_url or "&sslmode=require" in db_url:
    # Remove sslmode from URL and configure SSL via connect_args for asyncpg
    parsed = urlparse(db_url)
    query_params = parse_qs(parsed.query)
    
    if "sslmode" in query_params:
        sslmode = query_params.pop("sslmode")[0]
        # Rebuild URL without sslmode
        new_query = urlencode(query_params, doseq=True)
        parsed = parsed._replace(query=new_query)
        db_url = urlunparse(parsed)
        
        # Configure SSL for asyncpg - Railway uses self-signed certs, so disable verification
        if sslmode == "require":
            # Create SSL context that accepts self-signed certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connect_args["ssl"] = ssl_context

engine = create_async_engine(
    db_url,
    pool_pre_ping=True,
    echo=settings.app_env == "development",
    connect_args=connect_args if connect_args else {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_session() -> AsyncSession:
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
