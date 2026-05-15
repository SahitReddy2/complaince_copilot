import openai
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from backend.database.models import Regulation, ProhibitedIngredient, ClaimRestriction
from backend.extractors.ingredient_extractor import ExtractedIngredient
from backend.extractors.claim_extractor import ExtractedClaim

class ComplianceAgent:
    def __init__(self, openai_api_key: str, db: Session):
        self.client = openai.OpenAI(api_key=openai_api_key)
        self.db = db
    
    def analyze_product_compliance(self, 
                                 ingredients: List[ExtractedIngredient],
                                 claims: List[ExtractedClaim],
                                 jurisdiction: str = "US") -> Dict:
        """Comprehensive compliance analysis for a product."""
        
        results = {
            "overall_status": "pending",
            "jurisdiction": jurisdiction,
            "ingredient_compliance": self.check_ingredient_compliance(ingredients, jurisdiction),
            "claim_compliance": self.check_claim_compliance(claims, jurisdiction),
            "recommendations": [],
            "violations": [],
            "warnings": []
        }
        
        # Determine overall status
        has_violations = (
            results["ingredient_compliance"]["violations"] or
            results["claim_compliance"]["violations"]
        )
        
        has_warnings = (
            results["ingredient_compliance"]["warnings"] or
            results["claim_compliance"]["warnings"]
        )
        
        if has_violations:
            results["overall_status"] = "non_compliant"
        elif has_warnings:
            results["overall_status"] = "warning"
        else:
            results["overall_status"] = "compliant"
        
        # Generate recommendations
        results["recommendations"] = self.generate_recommendations(results)
        
        return results
    
    def check_ingredient_compliance(self, ingredients: List[ExtractedIngredient], jurisdiction: str) -> Dict:
        """Check ingredient compliance against regulations."""
        
        compliance_result = {
            "status": "compliant",
            "violations": [],
            "warnings": [],
            "compliant_ingredients": []
        }
        
        # Get prohibited ingredients for jurisdiction
        prohibited_ingredients = self.db.query(ProhibitedIngredient).join(
            Regulation
        ).filter(
            Regulation.jurisdiction == jurisdiction
        ).all()
        
        # Create lookup dictionaries
        banned_ingredients = {pi.ingredient_name.lower(): pi for pi in prohibited_ingredients if pi.is_banned}
        restricted_ingredients = {pi.ingredient_name.lower(): pi for pi in prohibited_ingredients if not pi.is_banned}
        
        for ingredient in ingredients:
            ingredient_name_lower = ingredient.ingredient_name.lower()
            
            # Check if ingredient is banned
            if ingredient_name_lower in banned_ingredients:
                violation = {
                    "type": "banned_ingredient",
                    "ingredient": ingredient.ingredient_name,
                    "severity": "high",
                    "description": f"Ingredient '{ingredient.ingredient_name}' is banned in {jurisdiction}",
                    "regulatory_reference": banned_ingredients[ingredient_name_lower].regulation.regulation_name,
                    "action_required": "Remove ingredient from formulation"
                }
                compliance_result["violations"].append(violation)
                compliance_result["status"] = "non_compliant"
            
            # Check concentration limits
            elif ingredient_name_lower in restricted_ingredients:
                restricted = restricted_ingredients[ingredient_name_lower]
                if ingredient.concentration and restricted.max_concentration:
                    if ingredient.concentration > float(restricted.max_concentration):
                        violation = {
                            "type": "concentration_limit",
                            "ingredient": ingredient.ingredient_name,
                            "severity": "high",
                            "description": f"Concentration {ingredient.concentration}% exceeds limit of {restricted.max_concentration}%",
                            "regulatory_reference": restricted.regulation.regulation_name,
                            "action_required": f"Reduce concentration to {restricted.max_concentration}% or below"
                        }
                        compliance_result["violations"].append(violation)
                        compliance_result["status"] = "non_compliant"
                    else:
                        compliance_result["compliant_ingredients"].append(ingredient.ingredient_name)
                else:
                    # Concentration not specified - warning
                    warning = {
                        "type": "concentration_unknown",
                        "ingredient": ingredient.ingredient_name,
                        "severity": "medium",
                        "description": f"Concentration not specified for restricted ingredient '{ingredient.ingredient_name}'",
                        "regulatory_reference": restricted.regulation.regulation_name,
                        "action_required": "Specify concentration and ensure it's within limits"
                    }
                    compliance_result["warnings"].append(warning)
            
            # Check for common allergens
            elif ingredient.is_allergen:
                warning = {
                    "type": "allergen_declaration",
                    "ingredient": ingredient.ingredient_name,
                    "severity": "medium",
                    "description": f"Allergen '{ingredient.ingredient_name}' must be properly declared",
                    "action_required": "Ensure allergen is listed in ingredients and on label"
                }
                compliance_result["warnings"].append(warning)
            
            else:
                compliance_result["compliant_ingredients"].append(ingredient.ingredient_name)
        
        return compliance_result
    
    def check_claim_compliance(self, claims: List[ExtractedClaim], jurisdiction: str) -> Dict:
        """Check marketing claim compliance."""
        
        compliance_result = {
            "status": "compliant",
            "violations": [],
            "warnings": [],
            "compliant_claims": []
        }
        
        # Get claim restrictions for jurisdiction
        claim_restrictions = self.db.query(ClaimRestriction).join(
            Regulation
        ).filter(
            Regulation.jurisdiction == jurisdiction
        ).all()
        
        # Create lookup for prohibited terms
        prohibited_terms = []
        for restriction in claim_restrictions:
            if restriction.prohibited_terms:
                prohibited_terms.extend(restriction.prohibited_terms)
        
        for claim in claims:
            claim_lower = claim.claim_text.lower()
            
            # Check for prohibited terms
            found_prohibited = [term for term in prohibited_terms if term.lower() in claim_lower]
            
            if found_prohibited:
                violation = {
                    "type": "prohibited_claim",
                    "claim": claim.claim_text,
                    "severity": "high",
                    "description": f"Claim contains prohibited terms: {', '.join(found_prohibited)}",
                    "regulatory_reference": "FDA Cosmetic Labeling Requirements",
                    "action_required": "Remove or modify claim to comply with regulations"
                }
                compliance_result["violations"].append(violation)
                compliance_result["status"] = "non_compliant"
            
            # Check claim severity
            elif claim.severity == "high":
                violation = {
                    "type": "high_risk_claim",
                    "claim": claim.claim_text,
                    "severity": "high",
                    "description": f"High-risk claim: {claim.claim_text}",
                    "potential_issues": claim.potential_issues,
                    "action_required": "Provide substantiation or remove claim"
                }
                compliance_result["violations"].append(violation)
                compliance_result["status"] = "non_compliant"
            
            elif claim.severity == "medium":
                warning = {
                    "type": "medium_risk_claim",
                    "claim": claim.claim_text,
                    "severity": "medium",
                    "description": f"Medium-risk claim requires substantiation: {claim.claim_text}",
                    "potential_issues": claim.potential_issues,
                    "action_required": "Provide supporting evidence or modify claim"
                }
                compliance_result["warnings"].append(warning)
            
            else:
                compliance_result["compliant_claims"].append(claim.claim_text)
        
        return compliance_result
    
    def generate_recommendations(self, analysis_results: Dict) -> List[str]:
        """Generate actionable recommendations based on compliance analysis."""
        
        recommendations = []
        
        # Ingredient recommendations
        ingredient_violations = analysis_results["ingredient_compliance"]["violations"]
        if ingredient_violations:
            banned_count = sum(1 for v in ingredient_violations if v["type"] == "banned_ingredient")
            if banned_count > 0:
                recommendations.append(f"Remove {banned_count} banned ingredient(s) from formulation")
            
            concentration_count = sum(1 for v in ingredient_violations if v["type"] == "concentration_limit")
            if concentration_count > 0:
                recommendations.append(f"Reduce concentration for {concentration_count} ingredient(s)")
        
        # Claim recommendations
        claim_violations = analysis_results["claim_compliance"]["violations"]
        if claim_violations:
            prohibited_count = sum(1 for v in claim_violations if v["type"] == "prohibited_claim")
            if prohibited_count > 0:
                recommendations.append(f"Remove or modify {prohibited_count} prohibited claim(s)")
            
            high_risk_count = sum(1 for v in claim_violations if v["type"] == "high_risk_claim")
            if high_risk_count > 0:
                recommendations.append(f"Provide substantiation for {high_risk_count} high-risk claim(s)")
        
        # General recommendations
        if analysis_results["overall_status"] == "compliant":
            recommendations.append("Product appears compliant with current regulations")
        
        return recommendations
    
    def get_regulatory_guidance(self, query: str, jurisdiction: str = "US") -> str:
        """Get regulatory guidance using AI."""
        
        prompt = f"""
        You are a cosmetics regulatory expert specializing in {jurisdiction} regulations.
        
        Provide guidance on the following query:
        {query}
        
        Please provide:
        1. Specific regulatory requirements
        2. Relevant citations (FDA, FTC, etc.)
        3. Recommended actions
        4. Potential consequences of non-compliance
        
        Keep the response practical and actionable.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error getting regulatory guidance: {e}"