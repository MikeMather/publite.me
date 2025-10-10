import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from alembic import command
from alembic.config import Config
from app import utils
from app.auth import SECRET_KEY
from app.crud import settings
from app.database import get_db
from app.middleware.static_cache import CacheableStaticFiles
from app.routers import admin_router, blog_router, import_router, media_router
from app.session import get_session


def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app_: FastAPI):
    print("Starting up...")
    print("run alembic upgrade head...")
    run_migrations()
    yield
    print("Shutting down...")


app = FastAPI(
    title="publite.me",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

STATIC_ROOT = os.getenv("STATIC_ROOT", "app/static")
MEDIA_ROOT = os.getenv("MEDIA_ROOT", "app/static/media")

os.makedirs(f"{MEDIA_ROOT}/original", exist_ok=True)
os.makedirs(f"{MEDIA_ROOT}/thumbnails", exist_ok=True)
os.makedirs(f"{MEDIA_ROOT}/medium", exist_ok=True)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.mount("/static", CacheableStaticFiles(directory=STATIC_ROOT), name="static")
app.mount("/media", CacheableStaticFiles(directory=MEDIA_ROOT), name="media")

templates = Jinja2Templates(directory="app/templates")

app.include_router(admin_router.router)
app.include_router(blog_router.router)
app.include_router(import_router.router)
app.include_router(media_router.router)


@app.middleware("http")
async def add_settings_and_session(request: Request, call_next):
    request.state.templates = templates
    db = next(get_db())
    try:
        request.state.settings = settings.get_settings(db)
        session = await get_session(request, db)
        response = await call_next(request)

        if isinstance(response, Response):
            session.save(response)

        return response
    except Exception as e:
        request.state.settings = None
        print(f"Request error: {e}")
        return await call_next(request)
    finally:
        db.close()


@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    if request.method in ("GET", "HEAD", "OPTIONS"):
        csrf_token = utils.generate_csrf_token()
        signed_token = utils.sign_csrf_token(csrf_token, SECRET_KEY)
        request.state.csrf_token = signed_token
        response = await call_next(request)
        response.set_cookie(
            key="csrf_token",
            value=signed_token,
            httponly=True,
            samesite="strict",
            secure=request.url.scheme == "https",
            max_age=3600,
        )
        return response

    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        cookie_token = request.cookies.get("csrf_token")
        if not cookie_token:
            return JSONResponse(
                status_code=403, content={"detail": "CSRF token missing"}
            )
        form_token = request.headers.get("X-CSRF-Token")

        if not form_token:
            try:
                body = await request.body()

                async def receive():
                    return {"type": "http.request", "body": body}

                request._receive = receive
                form_data = await request.form()
                form_token = form_data.get("csrf_token")
            except Exception:
                pass

        if not form_token or not utils.validate_csrf_token(form_token, SECRET_KEY):
            return JSONResponse(
                status_code=403, content={"detail": "Invalid CSRF token"}
            )

        request.state.csrf_token = cookie_token

    return await call_next(request)


@app.middleware("http")
async def set_csp_header(request: Request, call_next):
    nonce = utils.generate_csrf_token()
    request.state.csp_nonce = nonce

    response = await call_next(request)

    csp = "child-src 'self'; "

    response.headers["Content-Security-Policy"] = csp

    report_to = {
        "group": "csp-endpoint",
        "max_age": 10886400,
        "endpoints": [{"url": "/csp-report"}],
    }
    response.headers["Report-To"] = str(report_to)

    return response


@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: Exception):
    blog_settings = settings.get_settings(next(get_db()))
    return templates.TemplateResponse(
        "404.html",
        {"request": request, "settings": blog_settings},
        status_code=status.HTTP_404_NOT_FOUND,
    )


@app.exception_handler(500)
async def custom_500_handler(request: Request, exc: Exception):
    return templates.TemplateResponse(
        "catchall.html",
        {"request": request, "settings": settings.get_settings(next(get_db()))},
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@app.post("/csp-report")
async def csp_report(request: Request):
    try:
        report = await request.json()
        print(f"CSP Violation: {report}")
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        print(f"Error processing CSP report: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Invalid CSP report"},
        )
