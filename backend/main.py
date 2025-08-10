import os
import uuid
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image
import openai

# Load API key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

# Create FastAPI app
app = FastAPI()

# ✅ Enable CORS for all origins (frontend → backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Folder to store reports
REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    job_id = str(uuid.uuid4())
    results = []
    total_estimate = 0

    for file in files:
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # For MVP: mock AI damage detection
        scope = f"Replace damaged drywall and repaint in {file.filename} location"
        line_items = [
            {"code": "DRY123", "desc": "Drywall replacement", "qty": 10, "price": 50, "total": 500},
            {"code": "PAINT45", "desc": "Repainting walls", "qty": 1, "price": 300, "total": 300},
        ]
        subtotal = sum(item["total"] for item in line_items)
        total_estimate += subtotal

        results.append({
            "image": file.filename,
            "scope": scope,
            "line_items": line_items,
            "subtotal": subtotal
        })

        os.remove(file_path)

    # Create PDF
    pdf_path = os.path.join(REPORTS_DIR, f"{job_id}_scope_report.pdf")
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.drawString(100, 750, f"Scope of Work Report - Job ID: {job_id}")
    y = 720
    for res in results:
        c.drawString(100, y, f"Image: {res['image']}")
        y -= 20
        c.drawString(100, y, f"Scope: {res['scope']}")
        y -= 20
        for item in res["line_items"]:
            c.drawString(120, y, f"{item['code']} - {item['desc']} - Qty: {item['qty']} - Unit: ${item['price']} - Total: ${item['total']}")
            y -= 15
        c.drawString(100, y, f"Subtotal: ${res['subtotal']}")
        y -= 30
    c.drawString(100, y, f"Total Estimate: ${total_estimate}")
    c.save()

    return JSONResponse({
        "job_id": job_id,
        "results": results,
        "total_estimate": total_estimate
    })

@app.get("/download/{job_id}")
async def download_report(job_id: str):
    pdf_path = os.path.join(REPORTS_DIR, f"{job_id}_scope_report.pdf")
    if not os.path.exists(pdf_path):
        return JSONResponse({"error": "Report not found"}, status_code=404)
    return FileResponse(pdf_path, filename=f"{job_id}_scope_report.pdf")
