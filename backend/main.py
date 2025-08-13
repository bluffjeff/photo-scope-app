import os
import uuid
import base64
import csv
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fpdf import FPDF
from PIL import Image
import google.generativeai as genai

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
CSV_PATH = os.path.join(BASE_DIR, "xactimate_ca.csv")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Load Xactimate Data
xactimate_data = {}
try:
    with open(CSV_PATH, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            code = row.get("Item") or row.get("Code")
            if code:
                xactimate_data[code.strip()] = {
                    "description": row.get("Description", ""),
                    "unit": row.get("Unit", ""),
                    "price": row.get("Price", "")
                }
    print(f"✅ Loaded {len(xactimate_data)} Xactimate items")
except FileNotFoundError:
    print(f"❌ CSV file not found: {CSV_PATH}")

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def analyze_damage_with_ai(image_paths):
    """Analyze damage using Google Gemini Vision Pro."""
    try:
        images = []
        for path in image_paths:
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

        model = genai.GenerativeModel("gemini-pro-vision")
        response = model.generate_content([prompt] + images)

        return response.text.strip()

    except Exception as e:
        return f"❌ AI analysis failed: {str(e)}"

def generate_pdf_report(job_id, analysis_text, image_paths):
    """Generate PDF report with thumbnails and AI analysis."""
    pdf_path = os.path.join(REPORTS_DIR, f"{job_id}_scope_report.pdf")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Scope of Work Report", ln=True, align="C")
    pdf.ln(10)

    # Add images as thumbnails
    for img_path in image_paths:
        try:
            img = Image.open(img_path)
            img.thumbnail((100, 100))
            thumb_path = os.path.join(UPLOAD_DIR, f"thumb_{os.path.basename(img_path)}")
            img.save(thumb_path)
            pdf.image(thumb_path, x=pdf.get_x(), y=pdf.get_y(), w=40)
            pdf.ln(45)
        except Exception as e:
            print(f"⚠️ Could not add image {img_path}: {e}")

    # AI Analysis Text
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 10, analysis_text)

    pdf.output(pdf_path)
    return pdf_path

@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    try:
        if not files:
            return {"error": "No files received"}

        job_id = str(uuid.uuid4())
        file_paths = []

        for file in files:
            save_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(save_path, "wb") as buffer:
                buffer.write(await file.read())
            file_paths.append(save_path)

        analysis_text = await analyze_damage_with_ai(file_paths)
        pdf_path = generate_pdf_report(job_id, analysis_text, file_paths)

        return {"job_id": job_id, "pdf_url": f"/download/{job_id}"}

    except Exception as e:
        import traceback
        err_log = traceback.format_exc()
        print(f"❌ Error in /upload: {e}\n{err_log}")
        return {"error": str(e), "details": err_log}

@app.get("/download/{job_id}")
async def download_report(job_id: str):
    pdf_path = os.path.join(REPORTS_DIR, f"{job_id}_scope_report.pdf")
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, filename=f"{job_id}_scope_report.pdf")
    return {"error": "Report not found"}
