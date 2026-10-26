from contextlib import asynccontextmanager, suppress
import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from project_paths import PROJECT_ROOT
from backend.db.repository import initialize
from backend.auth import router as auth
from backend.api import models,predictions,observations,cities,scenarios,feedback,workspace,municipal

@asynccontextmanager
async def lifespan(app):
    initialize()
    from backend.services.live_service import initialize as init_live,poll
    init_live()
    task=asyncio.create_task(poll())
    try: yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError): await task

app=FastAPI(title='CivicFlux research and civic resilience API',version='2.0.0',lifespan=lifespan)
for router in [auth,models.router,predictions.router,observations.router,cities.router,scenarios.router,feedback.router,workspace.router,municipal.router]:app.include_router(router)
@app.get('/api/health')
def health():return {'status':'ok','research_only':True,'automatic_dispatch':False}
dist=PROJECT_ROOT/'frontend/dist'
if dist.exists():app.mount('/',StaticFiles(directory=dist,html=True),name='frontend')
