import os
import uuid
import traceback
import pandas as pd
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fpdf import FPDF
import google.generativeai as genai

# ========== Setup ==========
app = FastAPI()
UPLOAD_DIR = "uploads"
REPORT_DIR = "reports"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Backend base URL (used for PDF links)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ========== Load Xactimate CSV ==========
xactimate_data = {}
possible_paths = [
    os.path.join("backend", "xactimate_ca.csv"),
    "xactimate_ca.csv"
]

csv_path = None
for path in possible_paths:
    abs_path = os.path.abspath(path)
    print(f"🔎 Checking for CSV at: {abs_path}")
    if os.path.exists(path):
        csv_path = path
        break

if csv_path:
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
        expected_headers = {"Item", "Description", "Unit", "Price"}
        if set(df.columns) >= expected_headers:
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
            print(f"❌ CSV header mismatch: {df.columns.tolist()}")
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
else:
    print("⚠️ CSV not found in any known location, continuing without pricing data")

# ========== AI Analysis ==========
async def analyze_damage_with_ai(image_paths):
    print("🔍 Starting AI analysis...")
    try:
        images = []
        for path in image_paths:
            with open(path, "rb") as f:
                images.append({"mime_type": "image/jpeg", "data": f.read()})

        prompt = (
            "You are a property damage estimation expert for water/fire/mold mitigation. "
            "Analyze the uploaded images and produce a clear scope of work with estimated "
            "California Xactimate costs. Format as:\n\n"
            "1. Summary of visible damage\n"
            "2. Detailed line items (code, description, qty, unit, cost)\n"
            "3. Total estimated cost"
        )

        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        response = model.generate_content([prompt] + images)

        print("✅ AI analysis complete")
        return response.text.strip()

    except Exception as e:
        print(f"❌ AI analysis error: {e}")
        traceback.print_exc()
        return "⚠️ AI analysis failed. Please retry later."

# ========== Upload Endpoint ==========
@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    job_id = str(uuid.uuid4())
    saved_files = []

    print(f"📥 Received upload request (job_id={job_id})")

    try:
        # Save uploaded files
        for file in files:
            file_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
            with open(file_path, "wb") as f:
                f.write(await file.read())
            saved_files.append(file_path)

        print(f"✅ Saved {len(saved_files)} files")

        # Run AI safely
        ai_result = await analyze_damage_with_ai(saved_files)

        # Generate PDF report (always)
        pdf_path = os.path.join(REPORT_DIR, f"{job_id}_scope_report.pdf")
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, txt="Scope of Work Report", ln=True, align="C")
        pdf.ln(10)

        # Add thumbnails
        for path in saved_files:
            try:
                pdf.image(path, w=60)
                pdf.ln(5)
            except Exception as e:
                print(f"⚠️ Skipped thumbnail for {path}: {e}")

        pdf.multi_cell(0, 10, ai_result)

        pdf.output(pdf_path)
        print(f"📝 PDF generated at {pdf_path}")

        return {"file_path": f"{BACKEND_URL}/download/{job_id}"}

    except Exception as e:
        print(f"❌ Fatal error in upload: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

# ========== Download Endpoint ==========
@app.get("/download/{job_id}")
async def download_report(job_id: str):
    pdf_path = os.path.join(REPORT_DIR, f"{job_id}_scope_report.pdf")
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, filename="scope_report.pdf", media_type="application/pdf")
    return JSONResponse(status_code=404, content={"error": "Report not found"})
