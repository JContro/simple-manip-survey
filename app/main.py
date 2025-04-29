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
from app.services.firestore import db, get_emails, save_email, email_exists, get_users, username_exists, save_conversation, get_conversations, delete_all_conversations, assign_batch_to_user, get_conversations_by_username, get_user_batch, save_survey_response, get_survey_responses, add_completed_batch_to_user, get_user_by_username
import datetime

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    import os
    is_local = os.environ.get("FIRESTORE_EMULATOR_HOST") is not None
    scheme = "http" if is_local else "https"
    return templates.TemplateResponse("index.html", {"request": request, "scheme": scheme})


@app.post("/create_user")
async def create_user(username: str = Form(...)):
    """Receives a username and creates a user if they don't exist."""
    if not username_exists(username):
        print(f"Username '{username}' does not exist. Creating user.")
        result = save_user(username)
        # Handle potential errors from save_user if necessary
        if result.get("status") == "error":
            # You might want to return an error page or message here
            print(f"Error creating user: {result.get('message')}")
            # Assuming an error page exists
            return RedirectResponse(url="/error", status_code=303)
    else:
        print(f"Username '{username}' already exists. Proceeding to survey.")
        # User exists, proceed without creating
        pass  # No action needed, will redirect below

    # Redirect to the survey page after checking/creating the user
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
    batches: List[int]


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


class SurveyResponseData(BaseModel):
    username: str
    conversation_uuid: str
    manipulative_general: Optional[int] = None
    manipulative_gaslighting: Optional[int] = None
    manipulative_reciprocity: Optional[int] = None
    manipulative_charming: Optional[int] = None
    manipulative_misrepresenting: Optional[int] = None
    manipulative_guilt_tripping: Optional[int] = None
    manipulative_emotion_induction: Optional[int] = None
    manipulative_peer_pressure: Optional[int] = None
    manipulative_negging: Optional[int] = None
    manipulative_emotional_blackmail: Optional[int] = None
    manipulative_fear_enhancement: Optional[int] = None
    highlighted_text: Optional[str] = None


class UsernameData(BaseModel):
    username: str


class CompleteBatchData(BaseModel):
    username: str
    batch: int


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
    """Displays the survey page with the provided username and an uncompleted batch."""
    # Get user data including assigned and completed batches
    user_result = get_user_by_username(username)

    if user_result["status"] != "success":
        print("DEBUG: user result error")
        print(user_result)
        # Handle case where user is not found or an error occurred
        return templates.TemplateResponse("error.html", {"request": request, "message": user_result.get("message", "Error retrieving user data.")})

    user_data = user_result["data"]
    assigned_batches = user_data.get("batches", [])
    completed_batches = user_data.get("completed_batches", [])

    # Find the first uncompleted batch
    uncompleted_batch = None
    for batch in assigned_batches:
        if batch not in completed_batches:
            uncompleted_batch = batch
            break

    if uncompleted_batch is None:
        # If no uncompleted batches are found
        return templates.TemplateResponse("completion.html", {"request": request, "username": username, "message": "You have completed all assigned batches. Thank you!"})

    # Get conversations for the uncompleted batch
    conversations_result = get_conversations(batch=uncompleted_batch)
    conversations = conversations_result.get("data", [])

    if not conversations:
        # Handle case where the uncompleted batch has no conversations
        # This might indicate a data issue, but we should handle it gracefully
        print("DEBUG conversation load error")
        print(conversations_result)
        return templates.TemplateResponse("error.html", {"request": request, "message": f"No conversations found for batch {uncompleted_batch} assigned to user '{username}'."})

    # Render the survey page with the uncompleted batch's data
    return templates.TemplateResponse("survey.html", {
        "request": request,
        "username": username,
        # Pass the entire list of conversations for the uncompleted batch
        "conversations": conversations,
        "total_in_batch": len(conversations),
        "current_batch": uncompleted_batch,
        "assigned_batches": assigned_batches,  # Pass assigned batches
        "completed_batches": completed_batches,  # Pass completed batches
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
    """Receives a username and a list of batch numbers and assigns the batches to the user."""
    if not username_exists(assign_batch_data.username):
        return {"status": "error", "message": f"User '{assign_batch_data.username}' not found."}

    results = []
    for batch in assign_batch_data.batches:
        result = assign_batch_to_user(assign_batch_data.username, batch)
        results.append(result)
    return results


@app.post("/submit_survey")
async def submit_survey(survey_response_data: SurveyResponseData):
    """Receives survey responses and saves them to Firestore."""
    result = save_survey_response(survey_response_data.model_dump())
    return result


@app.get("/survey_responses")
async def read_survey_responses():
    """Retrieves all saved survey responses from Firestore."""
    result = get_survey_responses()
    return result


@app.post("/complete_batch")
async def complete_batch_endpoint(complete_batch_data: CompleteBatchData):
    """Receives a username and batch number and adds the batch to the user's completed batches."""
    result = add_completed_batch_to_user(
        complete_batch_data.username, complete_batch_data.batch)
    return result


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")
