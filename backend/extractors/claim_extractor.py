import openai
import json
import re
from typing import Dict, List, Optional
from pydantic import BaseModel

class ExtractedClaim(BaseModel):
    claim_text: str
    claim_type: str  # efficacy, safety, natural, anti-aging, etc.
    severity: str  # low, medium, high (for regulatory risk)
    potential_issues: List[str] = []
    substantiation_required: bool = False

class ClaimExtractor:
    def __init__(self, openai_api_key: str):
        self.client = openai.OpenAI(api_key=openai_api_key)
        
        # Define problematic claim patterns
        self.medical_terms = [
            "cure", "treat", "heal", "therapeutic", "medicine", "drug",
            "disease", "infection", "bacteria", "virus", "medical",
            "diagnose", "prevent disease", "antiviral", "antibacterial"
        ]
        
        self.drug_claims = [
            "fda approved", "clinically proven", "dermatologist tested",
            "medical grade", "pharmaceutical", "prescription strength"
        ]
        
        self.unsubstantiated_claims = [
            "miracle", "instant", "permanent", "guaranteed", "100% effective",
            "scientifically proven", "breakthrough", "revolutionary"
        ]
    
    def extract(self, document_text: str) -> List[ExtractedClaim]:
        """Extract marketing claims from document text."""
        
        prompt = f"""
        Extract all marketing and product claims from this cosmetic document.
        
        For each claim, identify:
        - claim_text: The exact claim text
        - claim_type: Type of claim (efficacy, safety, natural, anti-aging, whitening, acne, moisturizing, etc.)
        - severity: Risk level (low, medium, high) based on regulatory scrutiny
        - potential_issues: List any regulatory concerns
        - substantiation_required: true if claim requires scientific backing
        
        High-risk claims include:
        - Medical/therapeutic claims
        - Drug-like claims
        - Unsubstantiated superlatives
        - Disease prevention claims
        - Structure/function claims
        
        Medium-risk claims include:
        - Efficacy claims without proof
        - Anti-aging claims
        - Specific percentage improvements
        - "Clinical" or "dermatologist" references
        
        Low-risk claims include:
        - Basic function descriptions
        - Ingredient listings
        - Texture/sensory descriptions
        
        Return ONLY a JSON array, no other text.
        
        Document text:
        {document_text}
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                claims_data = json.loads(json_str)
                return [ExtractedClaim(**claim) for claim in claims_data]
            else:
                return []
                
        except Exception as e:
            print(f"Error extracting claims: {e}")
            return []
    
    def analyze_claim_risk(self, claim_text: str) -> Dict:
        """Analyze individual claim for regulatory risk."""
        
        claim_lower = claim_text.lower()
        issues = []
        severity = "low"
        
        # Check for medical claims
        if any(term in claim_lower for term in self.medical_terms):
            issues.append("Contains medical/therapeutic language")
            severity = "high"
        
        # Check for drug-like claims
        if any(term in claim_lower for term in self.drug_claims):
            issues.append("Contains drug-like claims")
            severity = "high"
        
        # Check for unsubstantiated claims
        if any(term in claim_lower for term in self.unsubstantiated_claims):
            issues.append("Contains unsubstantiated superlatives")
            if severity != "high":
                severity = "medium"
        
        # Check for specific efficacy claims
        efficacy_patterns = [
            r'\d+%\s*(better|improvement|reduction)',
            r'clinically\s*(proven|tested|validated)',
            r'reduces?\s*(wrinkles|fine lines|age spots)',
            r'prevents?\s*(aging|wrinkles|sun damage)'
        ]
        
        for pattern in efficacy_patterns:
            if re.search(pattern, claim_lower):
                issues.append("Contains specific efficacy claims requiring substantiation")
                if severity == "low":
                    severity = "medium"
                break
        
        return {
            "severity": severity,
            "issues": issues,
            "substantiation_required": severity in ["medium", "high"]
        }
    
    def categorize_claim_type(self, claim_text: str) -> str:
        """Categorize claim type based on content."""
        
        claim_lower = claim_text.lower()
        
        categories = {
            'anti-aging': ['anti-aging', 'anti age', 'wrinkle', 'fine lines', 'youthful', 'aging'],
            'moisturizing': ['moisturize', 'hydrate', 'dry skin', 'moisture', 'hydration'],
            'acne': ['acne', 'breakout', 'blemish', 'pimple', 'blackhead', 'whitehead'],
            'whitening': ['whitening', 'brightening', 'lightening', 'pigmentation', 'dark spots'],
            'sun_protection': ['spf', 'sunscreen', 'uv protection', 'sun protection'],
            'natural': ['natural', 'organic', 'botanical', 'plant-based', 'herbal'],
            'sensitive_skin': ['sensitive', 'gentle', 'hypoallergenic', 'non-irritating'],
            'efficacy': ['proven', 'effective', 'results', 'improvement', 'reduces'],
            'safety': ['safe', 'tested', 'approved', 'dermatologist', 'clinically'],
            'texture': ['smooth', 'soft', 'silky', 'creamy', 'lightweight', 'non-greasy']
        }
        
        for category, keywords in categories.items():
            if any(keyword in claim_lower for keyword in keywords):
                return category
        
        return 'general'
    
    def extract_from_marketing_material(self, text: str) -> List[ExtractedClaim]:
        """Extract claims specifically from marketing materials."""
        
        # Look for typical marketing sections
        marketing_patterns = [
            r'BENEFITS?\s*[:]\s*(.+?)(?:\n\n|\Z)',
            r'CLAIMS?\s*[:]\s*(.+?)(?:\n\n|\Z)',
            r'FEATURES?\s*[:]\s*(.+?)(?:\n\n|\Z)',
            r'DESCRIPTION\s*[:]\s*(.+?)(?:\n\n|\Z)',
        ]
        
        marketing_text = ""
        for pattern in marketing_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                marketing_text += match.group(1) + "\n"
        
        if not marketing_text:
            marketing_text = text
        
        return self.extract(marketing_text)