import os
import uuid
import csv
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from openai import OpenAI
from fpdf import FPDF

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Base directory of backend
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XACTIMATE_CSV = os.path.join(BASE_DIR, "xactimate_ca.csv")

client = OpenAI(api_key=OPENAI_API_KEY)

# Load Xactimate CSV into memory
# Load Xactimate CSV into memory
xactimate_data = {}
try:
    with open(XACTIMATE_CSV, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        
        # Normalize headers to lowercase without spaces
        field_map = {name.strip().lower(): name for name in reader.fieldnames}

        code_col = field_map.get("item")
        desc_col = field_map.get("description")
        unit_col = field_map.get("unit")
        price_col = field_map.get("price")

        if not all([code_col, desc_col, unit_col, price_col]):
            raise KeyError(f"Missing one of required headers: {reader.fieldnames}")

        for row in reader:
            code = row[code_col].strip()
            xactimate_data[code] = {
                "description": row[desc_col],
                "unit": row[unit_col],
                "price": float(row[price_col])
            }

# FastAPI setup
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Photo Scope API is running 🚀"}

async def analyze_damage_with_ai(image_path: str):
    """
    Sends the uploaded image to GPT-4o-mini for damage assessment.
    """
    with open(image_path, "rb") as img_file:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an insurance damage assessment AI."},
                {"role": "user", "content": "Analyze the uploaded image for visible property damage. "
                                             "Return a JSON array where each element contains: "
                                             "code, description, quantity, and estimated total cost "
                                             "using California Xactimate pricing where possible."}
            ],
            temperature=0
        )

    ai_text = response.choices[0].message.content
    return ai_text

def generate_pdf_report(job_id: str, ai_result: str):
    """
    Creates a PDF report from AI analysis result.
    """
    pdf_dir = os.path.join(BASE_DIR, "reports")
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, f"{job_id}_scope_report.pdf")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=14)
    pdf.cell(200, 10, txt="Scope of Work & Estimate", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 8, ai_result)

    pdf.output(pdf_path)
    return pdf_path

@app.post("/upload")
async def upload_files(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    upload_dir = os.path.join(BASE_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    ai_result = await analyze_damage_with_ai(file_path)
    pdf_path = generate_pdf_report(job_id, ai_result)

    return {"job_id": job_id, "pdf_url": f"/download/{job_id}"}

@app.get("/download/{job_id}")
async def download_report(job_id: str):
    pdf_path = os.path.join(BASE_DIR, "reports", f"{job_id}_scope_report.pdf")
    if not os.path.exists(pdf_path):
        return {"error": "Report not found"}
    return FileResponse(pdf_path, filename=f"{job_id}_scope_report.pdf")

@app.get("/download-json/{job_id}")
async def download_json(job_id: str):
    json_path = os.path.join(BASE_DIR, "reports", f"{job_id}_scope_report.json")
    if not os.path.exists(json_path):
        return {"error": "JSON report not found"}
    return FileResponse(json_path, filename=f"{job_id}_scope_report.json")
