from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles


class CacheableStaticFiles(StaticFiles):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)

        response.headers["Cache-Control"] = "public, max-age=604800"

        if path.endswith((".css", ".js")):
            response.headers["Cache-Control"] = "public, max-age=86400"
        elif path.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")):
            response.headers["Cache-Control"] = "public, max-age=2592000"

        return response
