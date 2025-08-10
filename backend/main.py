import os
import uuid
import base64
import requests
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image
import openai

# Load API key
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, use your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

async def analyze_damage_with_ai(image_path: str):
    """Send image to OpenAI Vision API and return structured scope + line items."""
    with open(image_path, "rb") as img_file:
        img_bytes = img_file.read()
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")

    prompt = """
    You are an insurance restoration estimator for property damage in Sunnyvale & Palo Alto, California.
    Look at the attached photo and:
    1. Identify the type of damage (water, fire, mold, structural, etc.).
    2. Provide a short Scope of Work.
    3. List 2-5 relevant Xactimate line items with:
       - code
       - description
       - quantity (approx)
       - unit price in California (Sunnyvale/Palo Alto area)
       - total price
    Return JSON only, in this format:
    {
      "scope": "...",
      "line_items": [
        {"code": "XXX123", "desc": "...", "qty": 1, "price": 100, "total": 100}
      ]
    }
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # Vision-capable model
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
        ai_text = response.choices[0].message["content"]
        import json
        return json.loads(ai_text)
    except Exception as e:
        return {
            "scope": "Unable to determine damage",
            "line_items": []
        }

@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    job_id = str(uuid.uuid4())
    results = []
    total_estimate = 0

    for file in files:
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # 🔹 Call AI for actual damage assessment
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
