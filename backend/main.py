import os
import uuid
import json
import base64
from datetime import datetime
from typing import List
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image
import openai

# === Directories ===
UPLOAD_DIR = "uploads"
REPORT_DIR = "reports"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# === API Key ===
openai.api_key = os.getenv("OPENAI_API_KEY")

# === Bay Area / Santa Clara County Xactimate Codes ===
XACTIMATE_CODES = """
Common Xactimate Line Items (Bay Area / Santa Clara County Pricing):

--- WATER DAMAGE ---
WTR-101 | Water extraction, per hour, per technician | $205/hour
WTR-102 | Carpet water extraction, per sq. ft. | $3.40/sq.ft.
DRY-202 | Dehumidifier rental, per day | $55/day
DRY-203 | Air mover rental, per day | $35/day
CLN-303 | Antimicrobial application, per sq. ft. | $2.10/sq.ft.
CLN-304 | HEPA vacuuming, per sq. ft. | $1.05/sq.ft.
FRM-401 | Remove and replace drywall, per sq. ft. | $4.15/sq.ft.
FRM-402 | Remove and replace insulation, per sq. ft. | $1.80/sq.ft.
PAI-501 | Interior wall painting, per sq. ft. | $2.45/sq.ft.

--- FIRE DAMAGE ---
CLN-601 | Smoke odor removal with ozone machine, per day | $85/day
CLN-602 | Thermal fogging for smoke odor, per sq. ft. | $1.70/sq.ft.
CLN-603 | Soot cleaning, heavy, per sq. ft. | $2.70/sq.ft.
FRM-701 | Replace fire-damaged framing, per linear foot | $11.80/lf
FRM-702 | Replace roof decking, per sq. ft. | $4.95/sq.ft.
PAI-701 | Stain-block primer for smoke, per sq. ft. | $2.15/sq.ft.

--- MOLD REMEDIATION ---
CLN-801 | Mold remediation labor, per hour | $74/hour
CLN-802 | Negative air machine rental, per day | $60/day
CLN-803 | Containment barrier installation, per sq. ft. | $1.45/sq.ft.
CLN-804 | Removal & disposal of contaminated drywall, per sq. ft. | $3.50/sq.ft.
CLN-805 | Application of fungicidal sealant, per sq. ft. | $2.45/sq.ft.

--- STORM DAMAGE ---
FRM-901 | Emergency board-up, per sq. ft. | $6.20/sq.ft.
FRM-902 | Roof tarp installation, per sq. ft. | $4.70/sq.ft.
FRM-903 | Window replacement, standard size | $595/ea
FRM-904 | Siding repair, vinyl, per sq. ft. | $3.10/sq.ft.
FRM-905 | Fence panel replacement, wood, per panel | $100/ea
"""

# === FastAPI app ===
app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === AI Helper ===
def analyze_damage_with_ai(image_path):
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    img_b64 = base64.b64encode(img_bytes).decode()

    prompt = f"""
    You are a certified property insurance estimator working in Sunnyvale, Palo Alto, and surrounding Santa Clara County areas in California.
    These locations have higher-than-average labor and material costs due to Bay Area pricing.
    Look at this damage photo and:
    1. Write a 1-2 sentence Scope of Work.
    2. Match damages to the most relevant Xactimate codes from the Bay Area pricing table below.
    3. Provide 3-6 realistic line items in JSON format with:
       code, desc, qty, price, total.
    4. Calculate the subtotal and include it in the JSON.
    Use only codes from the table. If unsure, choose the closest match.
    Return ONLY valid JSON.

    {XACTIMATE_CODES}
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert property damage estimator."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": f"data:image/jpeg;base64,{img_b64}"}
                    ]
                }
            ],
            temperature=0
        )

        result_text = response.choices[0].message["content"]
        return json.loads(result_text)

    except Exception as e:
        print("AI analysis error:", e)
        return {
            "scope": "Unable to analyze image automatically.",
            "line_items": [],
            "subtotal": 0
        }

# === Upload Route ===
@app.post("/upload")
async def upload_images(files: List[UploadFile] = File(...)):
    job_id = str(uuid.uuid4())
    results = []
    total_estimate = 0

    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # AI Analysis
        analysis = analyze_damage_with_ai(file_path)
        scope = analysis.get("scope", "No scope provided.")
        line_items = analysis.get("line_items", [])
        subtotal = analysis.get("subtotal", sum(item.get("total", 0) for item in line_items))
        total_estimate += subtotal

        results.append({
            "image": file.filename,
            "scope": scope,
            "line_items": line_items,
            "subtotal": subtotal
        })

    # === Create PDF Report ===
    pdf_path = os.path.join(REPORT_DIR, f"{job_id}_scope_report.pdf")
    c = canvas.Canvas(pdf_path, pagesize=letter)
    y = 750

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, f"Scope of Work Report - Job ID: {job_id}")
    y -= 20
    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 30

    # Total
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, f"Total Estimate: ${round(total_estimate, 2)}")
    y -= 30

    # Per Image Details
    for result in results:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, f"Image: {result['image']}")
        y -= 15
        c.setFont("Helvetica", 11)
        c.drawString(50, y, f"Scope: {result['scope']}")
        y -= 20

        # Table header
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, "Code")
        c.drawString(120, y, "Description")
        c.drawString(300, y, "Qty")
        c.drawString(350, y, "Unit Price")
        c.drawString(450, y, "Total")
        y -= 15
        c.setFont("Helvetica", 10)

        for item in result["line_items"]:
            c.drawString(50, y, str(item.get("code", "")))
            c.drawString(120, y, str(item.get("desc", "")))
            c.drawString(300, y, str(item.get("qty", "")))
            c.drawString(350, y, f"${item.get('price', 0)}")
            c.drawString(450, y, f"${item.get('total', 0)}")
            y -= 15
            if y < 50:
                c.showPage()
                y = 750

        # Subtotal
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, f"Subtotal: ${round(result['subtotal'], 2)}")
        y -= 30

    c.save()

    return {
        "job_id": job_id,
        "total_estimate": total_estimate,
        "results": results
    }

# === Download Route ===
@app.get("/download/{job_id}")
async def download_report(job_id: str):
    pdf_path = os.path.join(REPORT_DIR, f"{job_id}_scope_report.pdf")
    if not os.path.exists(pdf_path):
        return {"error": "Report not found"}
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{job_id}_scope_report.pdf")
