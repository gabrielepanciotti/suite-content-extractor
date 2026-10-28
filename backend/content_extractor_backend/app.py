from suite_backend_core import create_app

from .api import router

app = create_app()
app.include_router(router)
