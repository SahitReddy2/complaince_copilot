# backend/extract.py

import os
import pytesseract
from pdf2image import convert_from_path
import pdfplumber
import json

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DIR = os.path.join(BASE_DIR, "law_docs/raw_pdfs")
SUMMARY_DIR = os.path.join(BASE_DIR, "law_docs/summary")
OUTPUT_DIR = os.path.join(BASE_DIR, "data/extracted")
os.makedirs(OUTPUT_DIR, exist_ok=True) # creates output directory if it doesn't exist

# Inserts raw text into full_text for each page in each pdf file
def extract_from_pdf(pdf_path):
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages): # loops thorugh each page in the pdf
            text = page.extract_text()
            if text and text.strip():
                full_text += f"\n--- Page {i+1} (pdfplumber) ---\n{text}"
            else:
                images = convert_from_path(pdf_path, first_page=i+1, last_page=i+1, dpi=300)
                ocr_text = pytesseract.image_to_string(images[0])
                full_text += f"\n--- Page {i+1} (OCR) ---\n{ocr_text}"
    return full_text

# extracts text from pdf
def extract_from_txt(txt_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read()

# creates JSON format with metadata of source path, type, and category guess (for now)
# dumps (outputs) JSON formatted data into output_path (unique .json file in output directory for each pdf)
def write_json_output(text, source_path, data_type, category_guess):
    filename = os.path.splitext(os.path.basename(source_path))[0] + ".json"
    output_path = os.path.join(OUTPUT_DIR, filename)

    # structured JSON data
    payload = {
        "text": text,
        "metadata": {
            "source": source_path,
            "type": data_type,  # 'raw' or 'summary'
            "category": category_guess
        }
    }

    # dumps JSON data into output_path (overwrites if exists)
    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(payload, out, indent=2, ensure_ascii=False)
    print(f"✅ Saved: {output_path}")

# OCRs and extracts raw_data pdfs and text summaries
def extract_all():
    # Process raw_pdfs
    for fname in os.listdir(RAW_DIR):
        if fname.endswith(".pdf"):
            path = os.path.join(RAW_DIR, fname)
            print(f"🔍 Extracting raw PDF: {fname}")
            text = extract_from_pdf(path)
            category = fname.split(".")[0].lower()
            write_json_output(text, path, "raw", category)

    # Process summaries
    for fname in os.listdir(SUMMARY_DIR):
        path = os.path.join(SUMMARY_DIR, fname)
        if os.path.isfile(path):  # <-- Only process actual files
            print(f"📄 Reading summary: {fname}")
            text = extract_from_txt(path)
            category = fname.split(".")[0].lower()
            write_json_output(text, path, "summary", category)

if __name__ == "__main__":
    extract_all()
