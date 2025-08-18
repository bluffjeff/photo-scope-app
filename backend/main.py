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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ========== Load Xactimate CSV ==========
xactimate_data = {}
csv_path = None
for path in [os.path.join("backend", "xactimate_ca.csv"), "xactimate_ca.csv"]:
    abs_path = os.path.abspath(path)
    if os.path.exists(path):
        csv_path = path
        break

if csv_path:
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
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
            print(f"❌ CSV header mismatch: {df.columns.tolist()}")
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
else:
    print("⚠️ CSV not found, continuing without pricing data")

# ========== AI Analysis with Multi-Model Fallback ==========
async def analyze_damage_with_ai(image_paths):
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

    # Try Gemini Flash first
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([prompt] + images)
        print("✅ Gemini Flash used successfully")
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ Gemini Flash failed: {e}")

    # Fallback to Gemini Pro
    try:
        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        response = model.generate_content([prompt] + images)
        print("✅ Gemini Pro used successfully")
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ Gemini Pro failed: {e}")

    # Final Fallback → Xactimate template
    print("⚠️ Using fallback template with CSV data")
    sample_items = [
        ("WTR101", 3),
        ("CLN201", 2),
        ("DEM305", 50)
    ]

    report_lines = []
    total = 0
    for code, qty in sample_items:
        if code in xactimate_data:
            desc = xactimate_data[code]["desc"]
            unit = xactimate_data[code]["unit"]
            price = xactimate_data[code]["price"]
            cost = qty * price
            total += cost
            report_lines.append(
                f"{code} – {desc} – {qty} {unit} @ ${price:.2f}/{unit} = ${cost:.2f}"
            )
        else:
            report_lines.append(f"{code} – Not found in CSV – Qty: {qty}")

    return (
        "⚠️ AI analysis unavailable (quota exceeded or error).\n\n"
        "📌 Auto-generated Manual Report:\n\n"
        "1. Summary of visible damage:\n"
        "   - Water intrusion suspected, baseboards affected, drying equipment required.\n\n"
        "2. Suggested line items:\n" +
        "\n".join(report_lines) +
        f"\n\n3. Total estimated cost: ${total:.2f}\n"
    )

# ========== Upload Endpoint ==========
@app.post("/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    job_id = str(uuid.uuid4())
    saved_files = []

    try:
        for file in files:
            file_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
            with open(file_path, "wb") as f:
                f.write(await file.read())
            saved_files.append(file_path)

        ai_result = await analyze_damage_with_ai(saved_files)

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

        try:
            safe_text = ai_result.encode("latin-1", "replace").decode("latin-1")
        except Exception:
            safe_text = "⚠️ Error displaying analysis text (encoding issue)."

        pdf.multi_cell(0, 10, safe_text)
        pdf.output(pdf_path)

        return {"file_path": f"{BACKEND_URL}/download/{job_id}"}

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

# ========== Download Endpoint ==========
@app.get("/download/{job_id}")
async def download_report(job_id: str):
    pdf_path = os.path.join(REPORT_DIR, f"{job_id}_scope_report.pdf")
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, filename="scope_report.pdf", media_type="application/pdf")
    return JSONResponse(status_code=404, content={"error": "Report not found"})
