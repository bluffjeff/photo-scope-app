import os
import uuid
import shutil
import pandas as pd
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fpdf import FPDF
from typing import List

# ========== Setup ==========
app = FastAPI()
UPLOAD_DIR = "jobs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Allow frontend (Render static site) to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Load Xactimate CSV ==========
xactimate_data = {}
csv_path = os.path.join("backend", "xactimate_ca.csv")
if os.path.exists(csv_path):
    try:
        df = pd.read_csv(csv_path, encoding="utf-8", on_bad_lines="skip")
        if set(df.columns) >= {"Item", "Description", "Unit", "Price"}:
            for _, row in df.iterrows():
                try:
                    code = str(row["Item"]).strip()
                    desc = str(row["Description"]).strip()
                    unit = str(row["Unit"]).strip()
                    price = float(row["Price"])
                    xactimate_data[code] = {"desc": desc, "unit": unit, "price": price}
                except Exception:
                    continue
            print(f"✅ Loaded {len(xactimate_data)} Xactimate items from {csv_path}")
        else:
            print(f"⚠️ CSV header mismatch: {df.columns.tolist()}")
    except Exception as e:
        print(f"⚠️ Error loading CSV: {e}")
else:
    print("⚠️ CSV file not found, continuing without pricing")

# ========== PDF Class with UTF-8 support ==========
class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        # load DejaVuSans font for full UTF-8 support
        self.add_font("DejaVu", "", os.path.join("backend", "fonts", "DejaVuSans.ttf"), uni=True)
        self.set_font("DejaVu", size=12)

# ========== Endpoints ==========

@app.post("/upload-inspection")
async def upload_inspection(
    files: List[UploadFile] = File(...),
    notes: str = Form(...),
    scope: str = Form(...),
    sketch: UploadFile = File(None)
):
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_DIR, job_id, "inspection")
    os.makedirs(job_dir, exist_ok=True)

    # Save photos
    for f in files:
        with open(os.path.join(job_dir, f.filename), "wb") as out:
            shutil.copyfileobj(f.file, out)

    # Save notes & scope
    with open(os.path.join(UPLOAD_DIR, job_id, "notes.txt"), "w", encoding="utf-8") as f:
        f.write(notes)
    with open(os.path.join(UPLOAD_DIR, job_id, "scope.txt"), "w", encoding="utf-8") as f:
        f.write(scope)

    # Save sketch if provided
    if sketch:
        sketch_path = os.path.join(job_dir, sketch.filename)
        with open(sketch_path, "wb") as out:
            shutil.copyfileobj(sketch.file, out)

    return {"job_id": job_id, "message": "Inspection data uploaded"}


@app.post("/upload-work/{job_id}")
async def upload_work(job_id: str, files: List[UploadFile] = File(...)):
    job_dir = os.path.join(UPLOAD_DIR, job_id, "work")
    os.makedirs(job_dir, exist_ok=True)

    for f in files:
        with open(os.path.join(job_dir, f.filename), "wb") as out:
            shutil.copyfileobj(f.file, out)

    return {"job_id": job_id, "message": "Work photos uploaded"}


@app.get("/generate-report/{job_id}")
async def generate_report(job_id: str):
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    insp_dir = os.path.join(job_dir, "inspection")
    work_dir = os.path.join(job_dir, "work")
    report_path = os.path.join(job_dir, "final_report.pdf")

    if not os.path.exists(job_dir):
        raise HTTPException(status_code=404, detail="Job not found")

    pdf = PDF()
    pdf.add_page()

    # Title
    pdf.set_font("DejaVu", size=16)
    pdf.cell(0, 10, f"Inspection Report – Job {job_id}", ln=True, align="C")

    # Notes
    notes_path = os.path.join(job_dir, "notes.txt")
    if os.path.exists(notes_path):
        pdf.set_font("DejaVu", size=12)
        pdf.multi_cell(0, 10, f"Inspector Notes:\n{open(notes_path, encoding='utf-8').read()}")

    # Scope
    scope_path = os.path.join(job_dir, "scope.txt")
    if os.path.exists(scope_path):
        pdf.multi_cell(0, 10, f"\nScope (Team Entry):\n{open(scope_path, encoding='utf-8').read()}")

    # Inspection photos
    if os.path.exists(insp_dir):
        pdf.add_page()
        pdf.cell(0, 10, "Before Photos", ln=True)
        for img in os.listdir(insp_dir):
            if img.lower().endswith((".jpg", ".jpeg", ".png")):
                pdf.image(os.path.join(insp_dir, img), w=80)

    # Work photos
    if os.path.exists(work_dir):
        pdf.add_page()
        pdf.cell(0, 10, "After Photos", ln=True)
        for img in os.listdir(work_dir):
            if img.lower().endswith((".jpg", ".jpeg", ".png")):
                pdf.image(os.path.join(work_dir, img), w=80)

    # Xactimate line items (first 5 as placeholder)
    if xactimate_data:
        pdf.add_page()
        pdf.cell(0, 10, "Xactimate Line Items", ln=True)
        pdf.set_font("DejaVu", size=11)
        pdf.cell(40, 10, "Code")
        pdf.cell(90, 10, "Description")
        pdf.cell(30, 10, "Price", ln=True)
        for code, item in list(xactimate_data.items())[:5]:
            pdf.cell(40, 10, code)
            pdf.cell(90, 10, item["desc"][:40])  # truncate long desc
            pdf.cell(30, 10, f"${item['price']:.2f}", ln=True)

    pdf.output(report_path)
    return {"report_url": f"/download/{job_id}"}


@app.get("/download/{job_id}")
async def download_report(job_id: str):
    report_path = os.path.join(UPLOAD_DIR, job_id, "final_report.pdf")
    if not os.path.exists(report_path):
        return JSONResponse(status_code=404, content={"error": "Report not found"})
    return FileResponse(report_path, media_type="application/pdf", filename="report.pdf")