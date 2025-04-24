from fastapi import FastAPI
from app.services.firestore import db
import datetime

app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "World"}

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