from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.services.firestore import db, get_emails, save_email, email_exists, get_users, username_exists, save_conversation, get_conversations, delete_all_conversations
import datetime

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
@app.get("/signup", response_class=HTMLResponse)
async def signup(request: Request):
    return templates.TemplateResponse("survey.html", {"request": request})
from fastapi import Form, Depends
from app.services.firestore import save_user_and_survey

@app.post("/submit_survey")
async def submit_survey(
    username: str = Form(...),
    age: int = Form(None),
    gender: str = Form(None),
    education: str = Form(None)
):
    survey_data = {
        "age": age,
        "gender": gender,
        "education": education
    }
    result = save_user_and_survey(username, survey_data)
    return result

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
from typing import List, Dict, Any, Optional

class Message(BaseModel):
    role: str
    content: str

class Conversation(BaseModel):
    uuid: str
    title: str
    model: str
    context: str
    option: str
    prompt_type: str
    prompt: str
    manipulation_type: Optional[str] = None
    manipulation_description: Optional[str] = None
    chat_completion: str
    processing_time: float
    timestamp: int
    error: Optional[str] = None
    persuasion_strength: Optional[str] = None
    generated_text: Optional[str] = None
    cleaned_conversation: List[Message]
    batch: int

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

class UsernameData(BaseModel):
    username: str

@app.post("/check_username")
async def check_username_endpoint(username_data: UsernameData):
    """Receives a username and checks if it exists in Firestore."""
    if username_exists(username_data.username):
        print(f"Username '{username_data.username}' exists.")
        return {"status": "success"}
    else:
        print(f"Username '{username_data.username}' does not exist.")
        return {"status": "failure"}

@app.get("/emails")
async def read_emails():
    """Retrieves all saved emails from Firestore."""
    result = get_emails()
    return result

@app.get("/users")
async def read_users():
    """Retrieves all saved users from Firestore."""
    result = get_users()
    return result

@app.get("/healthcheck")
async def healthcheck():
    """Healthcheck endpoint to check if the application is running."""
    return {"status": "ok"}
@app.post("/conversations")
async def create_conversation(conversation: Conversation):
    """Receives a conversation and saves it to Firestore."""
    result = save_conversation(conversation.model_dump())
    return result

@app.get("/conversations")
async def read_conversations():
    """Retrieves all saved conversations from Firestore."""
    result = get_conversations()
    return result

@app.delete("/conversations")
async def reset_conversations():
    """Deletes all saved conversations from Firestore."""
    result = delete_all_conversations()
    return result

from fastapi.responses import FileResponse

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")