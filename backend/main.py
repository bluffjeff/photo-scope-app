import os
import uuid
import shutil
import pandas as pd
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fpdf import FPDF
from typing import List

app = FastAPI()

# Allow frontend (Render static site) to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("jobs", exist_ok=True)

# Load Xactimate CSV
XACTIMATE_FILE = "backend/xactimate_ca.csv"
xactimate_data = {}
if os.path.exists(XACTIMATE_FILE):
    try:
        df = pd.read_csv(XACTIMATE_FILE, encoding="utf-8", on_bad_lines="skip")
        for _, row in df.iterrows():
            code = str(row["Code"]).strip()
            desc = str(row["Description"]).strip()
            price = float(row["Unit Price"]) if row["Unit Price"] else 0
            xactimate_data[code] = {"desc": desc, "price": price}
        print(f"✅ Loaded {len(xactimate_data)} Xactimate items")
    except Exception as e:
        print(f"⚠️ Failed to load CSV: {e}")
else:
    print("⚠️ CSV file not found, continuing without pricing")


# ================== ENDPOINTS ==================

@app.post("/upload-inspection")
async def upload_inspection(
    files: List[UploadFile] = File(...),
    notes: str = Form(...),
    scope: str = Form(...),
    sketch: UploadFile = File(None)
):
    job_id = str(uuid.uuid4())
    job_dir = f"jobs/{job_id}/inspection"
    os.makedirs(job_dir, exist_ok=True)

    # Save photos
    for f in files:
        with open(os.path.join(job_dir, f.filename), "wb") as out:
            shutil.copyfileobj(f.file, out)

    # Save notes & scope
    with open(f"jobs/{job_id}/notes.txt", "w", encoding="utf-8") as f:
        f.write(notes)
    with open(f"jobs/{job_id}/scope.txt", "w", encoding="utf-8") as f:
        f.write(scope)

    # Save sketch if provided
    if sketch:
        sketch_path = os.path.join(job_dir, sketch.filename)
        with open(sketch_path, "wb") as out:
            shutil.copyfileobj(sketch.file, out)

    return {"job_id": job_id, "message": "Inspection data uploaded"}


@app.post("/upload-work/{job_id}")
async def upload_work(job_id: str, files: List[UploadFile] = File(...)):
    job_dir = f"jobs/{job_id}/work"
    os.makedirs(job_dir, exist_ok=True)

    for f in files:
        with open(os.path.join(job_dir, f.filename), "wb") as out:
            shutil.copyfileobj(f.file, out)

    return {"job_id": job_id, "message": "Work photos uploaded"}


@app.get("/generate-report/{job_id}")
async def generate_report(job_id: str):
    job_dir = f"jobs/{job_id}"
    insp_dir = os.path.join(job_dir, "inspection")
    work_dir = os.path.join(job_dir, "work")
    report_path = f"{job_dir}/final_report.pdf"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Inspection Report - Job {job_id}", ln=True, align="C")

    # Add notes
    notes_path = os.path.join(job_dir, "notes.txt")
    if os.path.exists(notes_path):
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 10, f"Inspector Notes:\n{open(notes_path).read()}")

    # Add scope
    scope_path = os.path.join(job_dir, "scope.txt")
    if os.path.exists(scope_path):
        pdf.multi_cell(0, 10, f"\nScope (Team Entry):\n{open(scope_path).read()}")

    # Add inspection photos
    if os.path.exists(insp_dir):
        pdf.add_page()
        pdf.cell(0, 10, "Before Photos", ln=True)
        for img in os.listdir(insp_dir):
            if img.lower().endswith((".jpg", ".png", ".jpeg")):
                pdf.image(os.path.join(insp_dir, img), w=80)

    # Add work photos
    if os.path.exists(work_dir):
        pdf.add_page()
        pdf.cell(0, 10, "After Photos", ln=True)
        for img in os.listdir(work_dir):
            if img.lower().endswith((".jpg", ".png", ".jpeg")):
                pdf.image(os.path.join(work_dir, img), w=80)

    # Xactimate Line Items (placeholder: random 2 items)
    pdf.add_page()
    pdf.cell(0, 10, "Xactimate Line Items", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(50, 10, "Code")
    pdf.cell(80, 10, "Description")
    pdf.cell(30, 10, "Price", ln=True)
    for code, item in list(xactimate_data.items())[:5]:
        pdf.cell(50, 10, code)
        pdf.cell(80, 10, item["desc"])
        pdf.cell(30, 10, f"${item['price']:.2f}", ln=True)

    pdf.output(report_path)
    return {"report_url": f"/download/{job_id}"}


@app.get("/download/{job_id}")
async def download_report(job_id: str):
    report_path = f"jobs/{job_id}/final_report.pdf"
    if not os.path.exists(report_path):
        return {"error": "Report not found"}
    return FileResponse(report_path, media_type="application/pdf", filename="report.pdf")
