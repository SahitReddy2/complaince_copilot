from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import os
from database.database import get_db
from agents.compliance_agent import ComplianceAgent
from extractors.ingredient_extractor import IngredientExtractor, ExtractedIngredient
from extractors.claim_extractor import ClaimExtractor, ExtractedClaim

router = APIRouter(prefix="/api/compliance", tags=["compliance"])

# Request/Response models
class ComplianceAnalysisRequest(BaseModel):
    ingredients: List[dict] = []
    claims: List[dict] = []
    jurisdiction: str = "US"
    product_name: Optional[str] = None

class ComplianceAnalysisResponse(BaseModel):
    overall_status: str
    jurisdiction: str
    ingredient_compliance: dict
    claim_compliance: dict
    recommendations: List[str]
    violations: List[dict]
    warnings: List[dict]

@router.post("/analyze", response_model=ComplianceAnalysisResponse)
async def analyze_compliance(
    request: ComplianceAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze product compliance against regulations.
    """
    try:
        # Initialize compliance agent
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        compliance_agent = ComplianceAgent(openai_api_key, db)
        
        # Convert request data to proper models
        ingredients = [ExtractedIngredient(**ingredient) for ingredient in request.ingredients]
        claims = [ExtractedClaim(**claim) for claim in request.claims]
        
        # Perform compliance analysis
        analysis_results = compliance_agent.analyze_product_compliance(
            ingredients=ingredients,
            claims=claims,
            jurisdiction=request.jurisdiction
        )
        
        return ComplianceAnalysisResponse(**analysis_results)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.get("/regulations/{jurisdiction}")
async def get_regulations(
    jurisdiction: str,
    db: Session = Depends(get_db)
):
    """
    Get regulations for a specific jurisdiction.
    """
    try:
        from database.models import Regulation
        
        regulations = db.query(Regulation).filter(
            Regulation.jurisdiction == jurisdiction
        ).all()
        
        return {
            "jurisdiction": jurisdiction,
            "regulations": [
                {
                    "id": str(reg.id),
                    "name": reg.regulation_name,
                    "effective_date": reg.effective_date.isoformat() if reg.effective_date else None,
                    "category": reg.category
                }
                for reg in regulations
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get regulations: {str(e)}")

@router.get("/prohibited-ingredients/{jurisdiction}")
async def get_prohibited_ingredients(
    jurisdiction: str,
    db: Session = Depends(get_db)
):
    """
    Get prohibited ingredients for a jurisdiction.
    """
    try:
        from database.models import ProhibitedIngredient, Regulation
        
        prohibited = db.query(ProhibitedIngredient).join(
            Regulation
        ).filter(
            Regulation.jurisdiction == jurisdiction
        ).all()
        
        return {
            "jurisdiction": jurisdiction,
            "prohibited_ingredients": [
                {
                    "ingredient_name": ing.ingredient_name,
                    "inci_name": ing.inci_name,
                    "cas_number": ing.cas_number,
                    "max_concentration": float(ing.max_concentration) if ing.max_concentration else None,
                    "is_banned": ing.is_banned,
                    "conditions": ing.conditions
                }
                for ing in prohibited
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get prohibited ingredients: {str(e)}")

@router.post("/guidance")
async def get_regulatory_guidance(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Get regulatory guidance for a specific query.
    """
    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        compliance_agent = ComplianceAgent(openai_api_key, db)
        
        guidance = compliance_agent.get_regulatory_guidance(
            query=request.get("query", ""),
            jurisdiction=request.get("jurisdiction", "US")
        )
        
        return {"guidance": guidance}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get guidance: {str(e)}")

@router.get("/jurisdictions")
async def get_supported_jurisdictions(db: Session = Depends(get_db)):
    """
    Get list of supported jurisdictions.
    """
    try:
        from database.models import Regulation
        
        jurisdictions = db.query(Regulation.jurisdiction).distinct().all()
        
        return {
            "jurisdictions": [j[0] for j in jurisdictions]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get jurisdictions: {str(e)}")