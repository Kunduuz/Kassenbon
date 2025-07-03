from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from processor import extract_products_from_image
import shutil
import uuid
import os

app = FastAPI()

# CORS aktivieren (für z. B. Flutter oder Web-Frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # für Produktion auf bestimmte Domains einschränken!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.get("/")
def root():
    return {"message": "OCR-API läuft ✅"}

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    try:
        file_ext = os.path.splitext(file.filename)[1]
        file_id = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_FOLDER, file_id)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

# 👇 wichtig für Render:
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

        result = extract_products_from_image(file_path)
        return {"success": True, "produkte": result}

    except Exception as e:
        return {"success": False, "error": str(e)}
