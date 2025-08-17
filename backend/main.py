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
    allow_origins=["*"],  # adjust for security later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Backend base URL (set in Render Env Var)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ========== Load Xactimate CSV ==========
xactimate_data = {}
csv_path = os.path.join("backend", "xactimate_ca.csv")
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
        print(f"✅ Loaded {len(xactimate_data)} Xactimate items")
    else:
        print(f"❌ CSV header mismatch: {df.columns.tolist()}")
except FileNotFoundError:
    print("⚠️ CSV not found, continuing without pricing data")


# ========== AI Analysis ==========
async def analyze_damage_with_ai(image_paths):
    print("🔍 Starting AI analysis...")
    try:
        images = []
        for path in image_paths:
            print(f"📷 Processing image for AI: {path}")
            with open(path, "rb") as f:
                images.append({"mime_type": "image/jpeg", "data": f.read()})

        prompt = (
            "You are a property damage estimation expert for water/fire/mold mitigation. "
            "Analyze the uploaded images and produce a detailed, human-readable scope of work "
            "with estimated California Xactimate costs. Avoid JSON, write in clear sections:\n"
            "1. Summary of visible damage\n"
            "2. Detailed line items with quantities, units, and costs\n"
            "3. Total estimated cost\n"
            "Format clearly for contractors."
        )

        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        response = model.generate_content([prompt] + images)

        print("✅ AI analysis complete")
        return response.text.strip()

    except Exception as e:
        print(f"❌ AI analysis error: {e}")
        traceback.print_exc()
        return f"AI analysis failed: {str(e)}"


# ========== PDF Generator ==========
def generate_pdf(job_id, analysis_text, image_paths):
    pdf_path = os.path.join(REPORT_DIR, f"{job_id}_scope_report.pdf")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Scope of Work Report", ln=True, align="C")

    # Insert thumbnails
    for img_path in image_paths:
        try:
            pdf.image(img_path, w=60, h=60)
        except Exception as e:
            print(f"⚠️ Could not add image {img_path}: {e}")

    # Insert analysis text
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 10, analysis_text)

    pdf.output(pdf_path)
    return pdf_path


# ========== API Endpoints ==========
@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    job_id = str(uuid.uuid4())
    print(f"📥 Received upload request (job_id={job_id})")

    saved_paths = []
    try:
        # Save uploaded images
        for file in files:
            file_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
            with open(file_path, "wb") as f:
                f.write(await file.read())
            saved_paths.append(file_path)
        print(f"✅ Saved {len(saved_paths)} files")

        # AI analysis
        ai_result = await analyze_damage_with_ai(saved_paths)

        # PDF generation
        print("📝 Generating PDF report...")
        pdf_path = generate_pdf(job_id, ai_result, saved_paths)

        # Build full URL for frontend
        pdf_url = f"{BACKEND_URL}/download/{job_id}"

        print(f"✅ Upload process complete: {pdf_url}")
        return {"job_id": job_id, "pdf_url": pdf_url, "message": "Report generated successfully"}

    except Exception as e:
        print(f"❌ Error in /upload: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/download/{job_id}")
async def download_report(job_id: str):
    pdf_path = os.path.join(REPORT_DIR, f"{job_id}_scope_report.pdf")
    if not os.path.exists(pdf_path):
        return JSONResponse(status_code=404, content={"error": "Report not found"})
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{job_id}_scope_report.pdf")


@app.get("/")
async def root():
    return {"message": "Backend running. Use /upload to submit files."}
