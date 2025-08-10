import os
import uuid
import base64
import csv
import json
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import openai

# Load API key
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, use your frontend Render URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

# Load Xactimate pricing CSV
XACTIMATE_CSV = "xactimate_ca.csv"
xactimate_data = {}

if os.path.exists(XACTIMATE_CSV):
    with open(XACTIMATE_CSV, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            code = row["code"].strip()
            xactimate_data[code] = {
                "desc": row["desc"].strip(),
                "price": float(row["price"])
            }

async def analyze_damage_with_ai(image_path: str):
    """Analyze photo with OpenAI Vision and map results to Xactimate CSV pricing."""
    with open(image_path, "rb") as img_file:
        img_bytes = img_file.read()
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")

    prompt = """
    You are an insurance restoration estimator specializing in Xactimate estimates for property damage in Sunnyvale & Palo Alto, California.

    Analyze the attached photo and:
    1. Identify the damage type (water, fire, mold, smoke, structural, etc.).
    2. Provide a short "Scope of Work" summary.
    3. Suggest 2-5 relevant Xactimate line item CODES (exact official codes when possible).
    4. If a code is unknown, use "UNKNOWN" but keep a clear description.
    5. Do NOT include pricing — we will handle pricing separately.
    6. Return strictly valid JSON only in this exact format:

    {
      "scope": "string",
      "line_items": [
        { "code": "string", "desc": "string", "qty": number }
      ]
    }

    ❗ Do NOT include any text outside the JSON.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a restoration estimator assistant."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": f"data:image/jpeg;base64,{img_base64}"}
                ]
            }
        ],
        temperature=0
    )

    try:
        ai_text = response.choices[0].message["content"].strip()
        parsed = json.loads(ai_text)
    except json.JSONDecodeError:
        return {
            "scope": "Unable to determine damage",
            "line_items": []
        }

    # Map pricing from CSV
    for item in parsed.get("line_items", []):
        code = item["code"].upper()
        if code in xactimate_data:
            item["desc"] = xactimate_data[code]["desc"]
            item["price"] = xactimate_data[code]["price"]
        else:
            item["price"] = 0.0
        item["total"] = round(item["qty"] * item["price"], 2)

    return parsed

@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    job_id = str(uuid.uuid4())
    results = []
    total_estimate = 0

    for file in files:
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())

        ai_result = await analyze_damage_with_ai(file_path)
        subtotal = sum(item["total"] for item in ai_result.get("line_items", []))
        total_estimate += subtotal

        results.append({
            "image": file.filename,
            "scope": ai_result.get("scope"),
            "line_items": ai_result.get("line_items", []),
            "subtotal": subtotal
        })

        os.remove(file_path)

    # Save PDF
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

    # Save raw JSON for auditing
    json_path = os.path.join(REPORTS_DIR, f"{job_id}_scope_data.json")
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump({
            "job_id": job_id,
            "results": results,
            "total_estimate": total_estimate
        }, jf, indent=2)

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

@app.get("/download-json/{job_id}")
async def download_json(job_id: str):
    json_path = os.path.join(REPORTS_DIR, f"{job_id}_scope_data.json")
    if not os.path.exists(json_path):
        return JSONResponse({"error": "Data not found"}, status_code=404)
    return FileResponse(json_path, filename=f"{job_id}_scope_data.json")
