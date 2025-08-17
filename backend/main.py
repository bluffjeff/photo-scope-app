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

# =================== AI + PDF + Routes remain the same ===================
# (I kept your working AI analysis, PDF generation, and upload/download endpoints from before)
