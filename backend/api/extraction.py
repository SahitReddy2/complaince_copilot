from datetime import datetime
import re
import sys
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
import os
import tempfile
from backend.database.database import get_db
from backend.extractors.ingredient_extractor import IngredientExtractor
from backend.extractors.claim_extractor import ClaimExtractor
import pdfplumber
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import docx
import traceback
import json
import subprocess

router = APIRouter(prefix="/api/extract", tags=["extraction"])

# Request/Response models
class TextExtractionRequest(BaseModel):
    text: str
    document_type: str = "general"

class TextExtractionResponse(BaseModel):
    extracted_text: str
    document_type: str
    metadata: dict = {}

@router.post("/text")
async def extract_text_from_file(
    file: UploadFile = File(...),
    document_type: str = "general"
):
    """
    Extract text from uploaded file (PDF, image, DOCX).
    """
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        extracted_text = ""
        metadata = {
            "filename": file.filename,
            "file_size": len(content),
            "file_type": file.content_type
        }
        
        # Extract text based on file type
        if file.content_type == "application/pdf":
            extracted_text = extract_text_from_pdf(tmp_file_path)
        elif file.content_type.startswith("image/"):
            extracted_text = extract_text_from_image(tmp_file_path)
        elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            extracted_text = extract_text_from_docx(tmp_file_path)
        else:
            # Try reading as text file
            with open(tmp_file_path, 'r', encoding='utf-8') as f:
                extracted_text = f.read()
        
        # Clean up temporary file
        os.unlink(tmp_file_path)
        
        return TextExtractionResponse(
            extracted_text=extracted_text,
            document_type=document_type,
            metadata=metadata
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {str(e)}")

@router.post("/ingredients")
async def extract_ingredients(
    request: TextExtractionRequest,
    # db: Session = Depends(get_db)
):
    """
    Extract ingredients from text using AI.
    """
    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        extractor = IngredientExtractor(openai_api_key)
        
        # Choose extraction method based on document type
        if request.document_type == "ingredient_list":
            ingredients = extractor.extract_from_ingredient_list(request.text)
        else:
            ingredients = extractor.extract(request.text)
        
        return {
            "ingredients": [ingredient.dict() for ingredient in ingredients],
            "count": len(ingredients)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingredient extraction failed: {str(e)}")

@router.post("/claims")
async def extract_claims(
    request: TextExtractionRequest,
    # db: Session = Depends(get_db)
):
    """
    Extract marketing claims from text using AI.
    """
    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        extractor = ClaimExtractor(openai_api_key)
        
        # Choose extraction method based on document type
        if request.document_type == "marketing_material":
            claims = extractor.extract_from_marketing_material(request.text)
        else:
            claims = extractor.extract(request.text)
        
        return {
            "claims": [claim.dict() for claim in claims],
            "count": len(claims)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Claim extraction failed: {str(e)}")

@router.post("/analyze-document")
async def analyze_document_comprehensive(
    file: UploadFile = File(...),
    jurisdiction: str = "US",
    # db: Session = Depends(get_db)
):
    """
    Comprehensive document analysis - extract text, ingredients, claims, and analyze compliance.
    """
    try:
        file_bytes = await file.read()

        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            tmp_file.write(file_bytes)
            tmp_file_path = tmp_file.name
        
        extracted_text = ""
        metadata = {
            "filename": file.filename,
            "file_size": len(file_bytes),
            "file_type": file.content_type
        }

        if file.content_type == "application/pdf":
            extracted_text = extract_text_from_pdf(tmp_file_path)
        elif file.content_type.startswith("image/"):
            extracted_text = extract_text_from_image(tmp_file_path)
        elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            extracted_text = extract_text_from_docx(tmp_file_path)
        else:
            with open(tmp_file_path, 'r', encoding='utf-8') as f:
                extracted_text = f.read()

        os.unlink(tmp_file_path)

        text_response = TextExtractionResponse(
            extracted_text=extracted_text,
            document_type="general",
            metadata=metadata
        )
        
        # text_response = await extract_text_from_file(file, "general")
        
        # Determine document type based on content
        document_type = classify_document_type(text_response.extracted_text)
        
        results = {
            "document_info": {
                "filename": file.filename,
                "document_type": document_type,
                "text_length": len(text_response.extracted_text)
            },
            "extracted_text": text_response.extracted_text,
            "ingredients": [],
            "claims": [],
            "compliance_analysis": {}
        }
        
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        # Extract ingredients if document contains ingredient info
        if "ingredient" in text_response.extracted_text.lower() or document_type == "ingredient_list":
            try:
                print("🧪 Attempting ingredient extraction...")
                ingredient_extractor = IngredientExtractor(openai_api_key)
                ingredients = ingredient_extractor.extract_from_ingredient_list(text_response.extracted_text)
                results["ingredients"] = [ingredient.dict() for ingredient in ingredients]
                print(f"✅ Extracted {len(ingredients)} ingredients.")
            except Exception as e:
                print(f"❌ Ingredient extraction failed: {e}")
                traceback.print_exc()
        
        if document_type != "ingredient_list":
            claim_extractor = ClaimExtractor(openai_api_key)
            claims = claim_extractor.extract(text_response.extracted_text)
            results["claims"] = [claim.dict() for claim in claims]
            print(f"✅ Extracted {len(claims)} claims.")
        else:
            print("Skipping claim extraction for ingredient list.")
        
        # Perform compliance analysis if we have extracted data
        if results["ingredients"] or results["claims"]:
            ingredient_names = [ing["ingredient_name"] for ing in results["ingredients"]]
            
            print("📝 Compliance input JSON:")
            print(json.dumps({"ingredients": ingredient_names}, indent=2))

            with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json") as f:
                ingredients_path = f.name
                json.dump({
                    "ingredients": ingredient_names,
                    "claims": [claim["claim_text"] for claim in results["claims"]]
                }, f)

            try:
                print("Running check_compliance.py...")
                proc = subprocess.run(
                    [sys.executable, "backend/check_compliance.py", ingredients_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8"
                )

                print("Compliance stdout:")
                print(proc.stdout)

                if proc.returncode != 0:
                    print(f"Compliance Script Failed: \n{proc.stderr}")
                    results["compliance_analysis"] = {
                        "error": "Compliance check failed",
                        "details": proc.stderr
                    }
                else:
                    try:
                        json_lines = proc.stdout.strip().splitlines()
                        last_line = json_lines[-1].strip()

                        # Print debug info
                        print("📤 Compliance script last line:")
                        print(last_line)

                        # Try parsing just the last line
                        compliance_data = json.loads(last_line)
                        results["compliance_analysis"] = compliance_data.get("non_compliant", [])

                        # Accquiring Information for Frontend
                        severity_counts = {
                            "critical": 0,
                            "high": 0,
                            "medium": 0,
                            "low": 0,
                            "resolved": 0
                        }

                        recent_issues_summary = []

                        for idx, issue in enumerate(results["compliance_analysis"]):
                            severity = issue.get("severity", "low").lower()
                            if severity in severity_counts:
                                severity_counts[severity] += 1
                            else:
                                severity_counts["low"] += 1 #(Requires unknown classification -> Added to LOW)

                            if idx < 3:
                                recent_issues_summary.append({
                                    "summary": issue.get("reason", "")[:100] + "...",
                                    "severity": severity,
                                    "law": issue.get("law", "Unknown Law")
                                })

                        penalty = (
                            severity_counts["critical"] * 20 +
                            severity_counts["high"] * 10 +
                            severity_counts["medium"] * 5 +
                            severity_counts["low"] * 2
                        )
                        compliance_score = max(0, 100-penalty)

                        results["compliance_score"] = compliance_score
                        results["issue_counts"] = severity_counts
                        results["recent_issues"] = recent_issues_summary

                        print(f"✅ Parsed {len(results['compliance_analysis'])} compliance results.")

                    except (json.JSONDecodeError, IndexError) as e:
                        print("❌ Failed to parse JSON:", e)
                        print("⚠️ Full stdout:")
                        print(proc.stdout)
                        results["compliance_analysis"] = {
                            "error": "Could not parse compliance output",
                            "raw_output": proc.stdout
                        }
                    print(f"Parse {len(compliance_data)} compliance results.")
            except Exception as e:
                print(f"Error running compliance script: {e}")
                results["compliance_analysis"] = {"error": str(e)}
            finally:
                os.unlink(ingredients_path)
        
        from uuid import uuid4
        from supabase import create_client

        SUPABASE_URL = "https://skflyrfklbfbxlvifyvw.supabase.co"
        SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNrZmx5cmZrbGJmYnhsdmlmeXZ3Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDUxNDQ4MCwiZXhwIjoyMDcwMDkwNDgwfQ.kmHpAr5w_GqF8fHpHMPDqffBjp0QgrJQh3B2dvfyW2I"
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise HTTPException(status_code=500, detail="Supabase credentials not configured")
        
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        ext = file.filename.split('.')[-1]
        unique_filename = f"{uuid4()}.{ext}"

        upload_response = supabase.storage.from_('reports').upload(
            path=unique_filename,
            file=file_bytes,
            file_options={"content-type": file.content_type}
        )
        print("📤 Upload response:", upload_response)

        file_url = supabase.storage.from_('reports').get_public_url(unique_filename)
        print(file_url)
        
        supabase.table("reports").insert({
            "filename": file.filename,
            "file_url": file_url,
            "created_at": datetime.utcnow().isoformat(),
            "claims": results.get("claims", []),
            "ingredients": results.get("ingredients", []),
            "compliance": results.get("compliance_analysis", []),
            "compliance_score": results.get("compliance_score", 0),
            "issue_counts": results.get("issue_counts", {}),
            "recent_issues": results.get("recent_issues", [])
        }).execute()
        
        return results
        
    except Exception as e:
        print("❌ Global exception in /analyze-document:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Document analysis failed: {str(e)}")

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file using pdfplumber, with OCR fallback via pytesseract."""
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        if not text.strip():
            print("⚠️ No extractable text found — falling back to OCR...")
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        img_path = f"temp_page_{page_num}.png"
                        # Save the page as an image file (safer fallback)
                        page.to_image(resolution=300).save(img_path, format="PNG")
                        image = Image.open(img_path)
                        ocr_text = pytesseract.image_to_string(image)
                        if ocr_text:
                            text += ocr_text + "\n"
                        os.remove(img_path)
                    except Exception as img_error:
                        print(f"❌ OCR failed for page {page_num}: {img_error}")
    except Exception as e:
        raise Exception(f"PDF extraction failed: {str(e)}")

    return text if text.strip() else "[No text could be extracted]"

def preprocess_image(image: Image.Image) -> Image.Image:
    image = image.convert("L")

    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)

    if image.size[0] < 1000:
        image = image.resize((image.size[0]*2, image.size[1]*2), Image.LANCZOS)
    
    image = image.filter(ImageFilter.SHARPEN)

    return image

def extract_text_from_image(file_path: str) -> str:
    try:
        print(f"📷 OCR extracting from image: {file_path}")
        image = Image.open(file_path)
        print(f"🧠 Image mode: {image.mode}, size: {image.size}, format: {image.format}")

        png_path = file_path.replace(".webp", ".png")
        image.save(png_path, format="PNG")
        image = preprocess_image(Image.open(png_path))

        if image.mode in ("P", "1"):
            image = image.convert("RGB")
        
        custom_config = r'--oem 3 --psm 6'

        text = pytesseract.image_to_string(image, lang='eng', config=custom_config)
        print(f"📝 OCR output: {text[:100]}...")
        return text if text.strip() else "[No text extracted by OCR]"
    except Exception as e:
        print(f"❌ Image OCR failed for {file_path}: {e}")
        raise

def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX file."""
    try:
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        raise Exception(f"DOCX extraction failed: {str(e)}")

def classify_document_type(text: str) -> str:
    """Classify document type based on content."""
    text_lower = text.lower()
    
    if "inci" in text_lower or "ingredients:" in text_lower:
        return "ingredient_list"
    elif any(word in text_lower for word in ["label", "packaging", "directions"]):
        return "product_label"
    elif any(word in text_lower for word in ["benefits", "claims", "effective", "proven"]):
        return "marketing_material"
    elif "safety" in text_lower or "sds" in text_lower:
        return "safety_data_sheet"
    elif "certificate" in text_lower or "test" in text_lower:
        return "certification"
    else:
        return "general"