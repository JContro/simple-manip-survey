from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.firestore import db, get_emails, save_email, email_exists
import datetime

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Custom url_for to force HTTPS for static files
    def url_for_https(name: str, **path_params: any) -> str:
        if name == "static":
            return str(request.url_for(name, **path_params).replace(scheme="https"))
        return str(request.url_for(name, **path_params))

    return templates.TemplateResponse("index.html", {"request": request, "url_for": url_for_https})

@app.post("/write_test_data")
async def write_test_data():
    """Writes a test document to Firestore."""
    try:
        test_doc_ref = db.collection("_test_collection").document("test_doc")
        test_doc_ref.set({"message": "Hello from FastAPI", "timestamp": datetime.datetime.now()})
        return {"status": "success", "message": "Test document written"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/read_test_data")
async def read_test_data():
    """Reads the test document from Firestore."""
    try:
        test_doc_ref = db.collection("_test_collection").document("test_doc")
        test_doc = test_doc_ref.get()
        if test_doc.exists:
            return {"status": "success", "data": test_doc.to_dict()}
        else:
            return {"status": "not found", "message": "Test document not found"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

from pydantic import BaseModel

class EmailData(BaseModel):
    email: str

@app.post("/save_email")
async def save_email_endpoint(email_data: EmailData):
    """Receives an email and saves it to Firestore, if it doesn't already exist."""
    if email_exists(email_data.email):
        print(f"Email '{email_data.email}' already exists, skipping save.")
        return {"status": "info", "message": "Email already exists"}
    else:
        result = save_email(email_data.email)
        return result

@app.get("/emails")
async def read_emails():
    """Retrieves all saved emails from Firestore."""
    result = get_emails()
    return result

@app.get("/healthcheck")
async def healthcheck():
    """Healthcheck endpoint to check if the application is running."""
    return {"status": "ok"}