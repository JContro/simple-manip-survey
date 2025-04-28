from fastapi.responses import FileResponse
from typing import Optional
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.services.firestore import save_user
from fastapi import Form, Depends
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.services.firestore import db, get_emails, save_email, email_exists, get_users, username_exists, save_conversation, get_conversations, delete_all_conversations, assign_batch_to_user, get_conversations_by_username, get_user_batch
import datetime

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/create_user")
async def create_user(username: str = Form(...)):
    """Receives a username and creates a user."""
    result = save_user(
        username)  # Assuming a new function save_user in firestore.py
    # Redirect to the survey page after creating the user
    return RedirectResponse(url=f"/survey/{username}", status_code=303)


@app.post("/write_test_data")
async def write_test_data():
    """Writes a test document to Firestore."""
    try:
        test_doc_ref = db.collection("_test_collection").document("test_doc")
        test_doc_ref.set({"message": "Hello from FastAPI",
                         "timestamp": datetime.datetime.now()})
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
    prompted_as: str
    manipulation_type: Optional[str] = None
    manipulation_description: Optional[str] = None
    chat_completion: str
    processing_time: float
    # timestamp: str
    error: Optional[str] = None
    persuasion_strength: Optional[str] = None
    generated_text: Optional[str] = None
    cleaned_conversation: List[Message]
    batch: int


class AssignBatchData(BaseModel):
    username: str
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


@app.get("/survey/{username}", response_class=HTMLResponse)
async def read_survey(request: Request, username: str):
    """Displays the survey page with the provided username and the first conversation."""
    # Assign a batch to the user if they don't have one
    # This logic needs to be implemented in firestore.py and potentially handle batch assignment strategy
    # For now, let's assume assign_batch_to_user handles this and returns the assigned batch number
    # Modify assign_batch_to_user to handle assignment if needed
    # Check if the user has an assigned batch
    user_batch_result = get_user_batch(username)
    assigned_batch = user_batch_result.get("batch")

    if not assigned_batch:
        # If no batch is assigned, we cannot proceed to get conversations.
        # The logic for assigning a new batch needs to be implemented.
        # For now, return an error message.
        return templates.TemplateResponse("error.html", {"request": request, "message": f"No batch assigned to user '{username}'. Batch assignment logic is not yet implemented."})

    # Get conversations for the assigned batch
    conversations_result = get_conversations(batch=assigned_batch)
    conversations = conversations_result.get("data", [])

    if not conversations:
        # Handle case where the assigned batch has no conversations
        return templates.TemplateResponse("error.html", {"request": request, "message": f"No conversations found for batch {assigned_batch}."})

    # Return the first conversation and batch information
    first_conversation = conversations[0]
    total_conversations_in_batch = len(conversations)

    return templates.TemplateResponse("survey.html", {
        "request": request,
        "username": username,
        "conversations": conversations,  # Pass the entire list of conversations
        "total_in_batch": len(conversations),
        "current_batch": assigned_batch,
        # Assuming total number of batches is available or can be calculated
        # "total_batches": total_batches
    })


@app.post("/conversations")
async def create_conversation(conversation: Conversation):
    """Receives a conversation and saves it to Firestore."""
    result = save_conversation(conversation.model_dump())
    return result


@app.get("/conversations")
async def read_conversations(batch: Optional[int] = None):
    """Retrieves saved conversations from Firestore, optionally filtered by batch."""
    result = get_conversations(batch=batch)
    return result


@app.delete("/conversations")
async def reset_conversations():
    """Deletes all saved conversations from Firestore."""
    result = delete_all_conversations()
    return result


@app.post("/assign_batch")
async def assign_batch_endpoint(assign_batch_data: AssignBatchData):
    """Receives a username and batch number and assigns the batch to the user."""
    result = assign_batch_to_user(
        assign_batch_data.username, assign_batch_data.batch)
    return result


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")
