import openai
import json
import re
from typing import Dict, List, Optional
from pydantic import BaseModel

class ExtractedIngredient(BaseModel):
    ingredient_name: str
    inci_name: Optional[str] = None
    concentration: Optional[float] = None
    function: Optional[str] = None
    cas_number: Optional[str] = None
    is_allergen: bool = False
    severity: str = "low"

class IngredientExtractor:
    def __init__(self, openai_api_key: str):
        self.client = openai.OpenAI(api_key=openai_api_key)
    
    def extract(self, document_text: str) -> List[ExtractedIngredient]:
        print("🧪 Extracting from:\n", document_text)
        """Extract ingredients from document text using OpenAI."""
        
        prompt = f"""
        Extract all cosmetic ingredients from this document text.

        For each ingredient, identify:
        - ingredient_name: Common name of the ingredient
        - inci_name: INCI (International Nomenclature of Cosmetic Ingredients) name if available
        - concentration: Percentage or concentration if mentioned
        - function: What the ingredient does (preservative, colorant, emulsifier, etc.)
        - cas_number: CAS registry number if available
        - is_allergen: true if it's a known allergen (like fragrance, essential oils, etc.)
        - severity: Risk level (low, medium, high) based on regulatory or allergen concern

        Severity rating guidelines:
        - High: Known allergens or restricted substances (fragrance, parfum, limonene, parabens, etc.)
        - Medium: Ingredients flagged for irritation or controversial (preservatives, some surfactants)
        - Low: Safe or common ingredients (moisturizers, thickeners, emulsifiers)

        Return ONLY a JSON array of ingredients, no other text.

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
            
            # Clean up the response to extract JSON
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                ingredients_data = json.loads(json_str)
                return [ExtractedIngredient(**ingredient) for ingredient in ingredients_data]
            else:
                return []
                
        except Exception as e:
            print(f"Error extracting ingredients: {e}")
            return []
    
    def extract_from_ingredient_list(self, ingredient_text: str) -> List[ExtractedIngredient]:
        patterns = [
            r'INGREDIENTS[\s\n]+(.+)',
            r'INGREDIENTS?\s*[:]\s*(.+)',
            r'INCI\s*[:]\s*(.+)',
            r'COMPOSITION\s*[:]\s*(.+)',
        ]

        ingredient_section = ""
        for pattern in patterns:
            match = re.search(pattern, ingredient_text, re.IGNORECASE | re.DOTALL)
            if match:
                ingredient_section = match.group(1)
                break

        if not ingredient_section:
            # fallback: look for the longest line with commas (naive fallback)
            lines = ingredient_text.splitlines()
            for line in lines:
                if "," in line and len(line) > 20:
                    ingredient_section = line
                    break

        return self.extract(ingredient_section)

    
    def validate_inci_name(self, inci_name: str) -> bool:
        """Validate INCI name format."""
        # Basic validation for INCI names
        if not inci_name:
            return False
        
        # INCI names should be in Latin/scientific format
        # Contains parentheses for specification
        # All caps or proper case
        return bool(re.match(r'^[A-Z][a-z]*(\s+[A-Z][a-z]*)*(\s*\([^)]+\))?$', inci_name))
    
    def categorize_ingredient_function(self, ingredient_name: str) -> str:
        """Categorize ingredient function based on name patterns."""
        
        ingredient_lower = ingredient_name.lower()
        
        function_keywords = {
            'preservative': ['paraben', 'benzoate', 'sorbate', 'phenoxyethanol', 'formaldehyde'],
            'colorant': ['ci ', 'fd&c', 'color', 'pigment', 'dye', 'iron oxide'],
            'fragrance': ['parfum', 'fragrance', 'essential oil', 'aroma'],
            'emulsifier': ['lecithin', 'stearate', 'cetyl', 'stearyl', 'emulsifying wax'],
            'moisturizer': ['glycerin', 'hyaluronic', 'ceramide', 'shea butter', 'aloe'],
            'surfactant': ['sulfate', 'glucoside', 'betaine', 'soap'],
            'thickener': ['carbomer', 'xanthan', 'guar gum', 'carrageenan'],
            'antioxidant': ['tocopherol', 'vitamin e', 'vitamin c', 'ascorbic', 'bht', 'bha'],
            'uv_filter': ['avobenzone', 'octinoxate', 'zinc oxide', 'titanium dioxide', 'spf']
        }
        
        for function, keywords in function_keywords.items():
            if any(keyword in ingredient_lower for keyword in keywords):
                return function
        
        return 'other'