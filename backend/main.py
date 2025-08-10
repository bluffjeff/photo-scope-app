import os
import uuid
import csv
import base64
import json
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
xactimate_data = {}
try:
    with open(XACTIMATE_CSV, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)

        field_map = {name.strip().lower(): name for name in reader.fieldnames}

        code_col = field_map.get("item")
        desc_col = field_map.get("description")
        unit_col = field_map.get("unit")
        price_col = field_map.get("price")

        if not all([code_col, desc_col, unit_col, price_col]):
            raise KeyError(f"Missing one of required headers: {reader.fieldnames}")

        for row in reader:
            code = row[code_col].strip()

            price_str = row[price_col].strip()
            try:
                price_val = float(price_str) if price_str else 0.0
            except ValueError:
                price_val = 0.0

            xactimate_data[code] = {
                "description": row[desc_col],
                "unit": row[unit_col],
                "price": price_val
            }

    print(f"✅ Loaded {len(xactimate_data)} Xactimate items")

except FileNotFoundError:
    print(f"❌ CSV file not found: {XACTIMATE_CSV}")
except KeyError as e:
    print(f"❌ CSV header mismatch: {e}")

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
    Sends the uploaded image to GPT-4o-mini for damage assessment with image input.
    """
    with open(image_path, "rb") as img_file:
        base64_image = base64.b64encode(img_file.read()).decode("utf-8")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an insurance damage assessment AI. Analyze uploaded property damage images."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Analyze this image for visible property damage. "
                            "Return a JSON array where each element contains: "
                            "code, description, quantity, unit, and price per unit "
                            "using California Xactimate pricing where possible."
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content

def generate_pdf_report(job_id: str, ai_result: str):
    """
    Creates a clean PDF report from AI JSON analysis result.
    """
    pdf_dir = os.path.join(BASE_DIR, "reports")
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, f"{job_id}_scope_report.pdf")

    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Scope of Work & Estimate", ln=True, align='C')
    pdf.ln(8)

    try:
        # Parse AI result as JSON
        items = json.loads(ai_result)
        if not isinstance(items, list):
            raise ValueError("AI result is not a JSON array")

        # Table headers
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(30, 10, "Code", border=1)
        pdf.cell(70, 10, "Description", border=1)
        pdf.cell(20, 10, "Qty", border=1, align='R')
        pdf.cell(20, 10, "Unit", border=1, align='R')
        pdf.cell(25, 10, "Price", border=1, align='R')
        pdf.cell(25, 10, "Total", border=1, align='R')
        pdf.ln()

        pdf.set_font("Arial", size=10)
        grand_total = 0.0

        for item in items:
            code = str(item.get("code", ""))
            desc = str(item.get("description", ""))[:40]
            qty = float(item.get("quantity", 0))
            unit = str(item.get("unit", ""))
            price = float(item.get("price", 0))
            total = price * qty
            grand_total += total

            pdf.cell(30, 8, code, border=1)
            pdf.cell(70, 8, desc, border=1)
            pdf.cell(20, 8, str(qty), border=1, align='R')
            pdf.cell(20, 8, unit, border=1, align='R')
            pdf.cell(25, 8, f"${price:,.2f}", border=1, align='R')
            pdf.cell(25, 8, f"${total:,.2f}", border=1, align='R')
            pdf.ln()

        # Grand total
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(165, 10, "Grand Total", border=1)
        pdf.cell(25, 10, f"${grand_total:,.2f}", border=1, align='R')

    except Exception as e:
        # Fallback: print raw AI output
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
