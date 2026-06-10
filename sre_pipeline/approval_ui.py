from fastapi import APIRouter, Request, FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sre_pipeline.db import Database
import os

ui_router = APIRouter()
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

db = Database()

@ui_router.get("/ui/queue", response_class=HTMLResponse)
def view_pending(request: Request, api_key: str = "") -> HTMLResponse:
    expected_api_key = os.getenv("SRE_API_KEY")
    if expected_api_key and api_key != expected_api_key:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Invalid API Key")
        
    pending_events = db.list_pending()
    return templates.TemplateResponse(
        request,
        "pending.html",
        {"events": pending_events}
    )
