from contextlib import asynccontextmanager
from typing import AsyncGenerator
import uuid, time, logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.database import init_db
from app.routers import auth, suppliers, certifications, financials, geopolitical, disruptions, alerts, alternatives, analytics, supplier_calls, ai

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    await init_db()
    if not settings.SKIP_SEED:
        try:
            from app.seed import seed_demo_data
            seed_result = await seed_demo_data()
            logger.info("Seed: %s", seed_result)
        except Exception as e:  # don't block startup on seed failure
            logger.warning("Seed failed: %s", e)
    yield


app = FastAPI(title="SupplierSense AI", version="1.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info("method=%s path=%s status=%d duration_ms=%.1f request_id=%s",
        request.method, request.url.path, response.status_code, duration_ms, request_id)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.exception("Unhandled exception request_id=%s: %s", request_id, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request_id})


@app.exception_handler(404)
async def not_found_handler(request: Request, exc) -> JSONResponse:
    detail = exc.detail if hasattr(exc, "detail") else "Resource not found"
    return JSONResponse(status_code=404, content={"detail": detail})


@app.exception_handler(405)
async def method_not_allowed_handler(request: Request, exc) -> JSONResponse:
    detail = exc.detail if hasattr(exc, "detail") else "Method not allowed"
    return JSONResponse(status_code=405, content={"detail": detail})


app.include_router(auth.router)
app.include_router(suppliers.router)
app.include_router(certifications.router)
app.include_router(financials.router)
app.include_router(geopolitical.router)
app.include_router(disruptions.router)
app.include_router(alerts.router)
app.include_router(alternatives.router)
app.include_router(analytics.router)
app.include_router(supplier_calls.router)
app.include_router(ai.router)


@app.get("/")
async def root():
    return {"message": "SupplierSense AI API", "version": "0.2.0"}


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}
