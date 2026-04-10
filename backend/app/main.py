from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
import time
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.core.config import settings
from app.core.env_verifier import verify_runtime_environment
from app.db.session import Base, engine
import app.db.models  # ensures models register
from app.modules.admin.router import router as admin_router
from app.modules.payments.router import router as payments_router
from app.modules.reports.router import router as reports_router
from app.modules.swarkigyan.router import router as swarkigyan_router
from app.modules.users.router import router as users_router


logging.basicConfig(level=logging.DEBUG if settings.DEBUG_LOGGING else logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compress large JSON payloads (reports list/detail) to reduce transfer size and load time.
app.add_middleware(
    GZipMiddleware,
    minimum_size=1500,
    compresslevel=6,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal Server Error",
        },
    )


@app.on_event("startup")
def startup_event():
    env_report = verify_runtime_environment()
    logger.info(
        "Runtime environment verification completed for %s",
        env_report.get("environment", "unknown"),
    )

    last_exc: Exception | None = None
    for attempt in range(1, 11):
        try:
            Base.metadata.create_all(bind=engine)

            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ")
                )
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR")
                )
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN IF NOT EXISTS mobile_number VARCHAR")
                )
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_verified BOOLEAN DEFAULT FALSE")
                )
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT FALSE")
                )
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN IF NOT EXISTS abuse_warnings INTEGER DEFAULT 0")
                )
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN IF NOT EXISTS signup_source VARCHAR")
                )
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN IF NOT EXISTS signup_ip VARCHAR")
                )
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN IF NOT EXISTS signup_user_agent VARCHAR")
                )
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN IF NOT EXISTS signup_referrer VARCHAR")
                )
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN IF NOT EXISTS signup_accept_language VARCHAR")
                )
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN IF NOT EXISTS signup_locale VARCHAR")
                )
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN IF NOT EXISTS signup_timezone VARCHAR")
                )
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN IF NOT EXISTS signup_city VARCHAR")
                )
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN IF NOT EXISTS signup_country VARCHAR")
                )
                connection.execute(
                    text("ALTER TABLE users ALTER COLUMN email DROP NOT NULL")
                )
                connection.execute(
                    text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_mobile_number ON users (mobile_number)")
                )
                connection.execute(
                    text("ALTER TABLE knowledge_assets ADD COLUMN IF NOT EXISTS domain VARCHAR")
                )
                connection.execute(
                    text("ALTER TABLE knowledge_assets ADD COLUMN IF NOT EXISTS approval_status VARCHAR DEFAULT 'pending'")
                )
                connection.execute(
                    text("ALTER TABLE knowledge_assets ADD COLUMN IF NOT EXISTS approved_by INTEGER")
                )
                connection.execute(
                    text("ALTER TABLE knowledge_assets ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ")
                )
                connection.execute(
                    text("ALTER TABLE knowledge_assets ADD COLUMN IF NOT EXISTS approval_notes TEXT")
                )
                connection.execute(
                    text("ALTER TABLE knowledge_assets ADD COLUMN IF NOT EXISTS manual_notes JSONB")
                )
                connection.execute(text("SELECT 1"))

            logger.info("Database connected and schema checks completed.")
            return
        except Exception as exc:
            last_exc = exc
            logger.warning("Database init attempt %s failed; retrying...", attempt)
            time.sleep(1.5)

    logger.exception("Startup initialization failed")
    raise RuntimeError("Database initialization failed") from last_exc


app.include_router(users_router, prefix="/api/users")
app.include_router(reports_router, prefix="/api/reports")
app.include_router(swarkigyan_router, prefix="/api/swarkigyan")
app.include_router(payments_router, prefix="/api/payments")
app.include_router(admin_router, prefix="/api/admin")


@app.get("/")
def root():
    return {
        "status": "Running",
        "engine_version": settings.ENGINE_VERSION,
    }


@app.get("/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        db_status = "connected"
    except SQLAlchemyError:
        db_status = "disconnected"

    return {
        "status": "healthy",
        "database": db_status,
    }
