"""
Seed script to populate the database with common cosmetics regulations
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlalchemy.orm import Session
from backend.database.database import SessionLocal, engine
from backend.database.models import Base, Regulation, ProhibitedIngredient, ClaimRestriction
from datetime import datetime

def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)

def seed_us_regulations(db: Session):
    """Seed US FDA cosmetics regulations."""
    
    # Create FDA regulation
    fda_regulation = Regulation(
        jurisdiction="US",
        regulation_name="FDA Cosmetic Regulations (21 CFR 700-740)",
        effective_date=datetime(2023, 1, 1),
        category="cosmetics",
        document_path="https://www.fda.gov/cosmetics/cosmetics-laws-regulations"
    )
    db.add(fda_regulation)
    db.flush()
    
    # Prohibited ingredients in US
    prohibited_ingredients = [
        {
            "ingredient_name": "Mercury compounds",
            "inci_name": "Mercury",
            "cas_number": "7439-97-6",
            "is_banned": True,
            "conditions": "All mercury compounds are prohibited except as preservatives in eye area cosmetics at 0.007% max"
        },
        {
            "ingredient_name": "Hexachlorophene",
            "inci_name": "Hexachlorophene",
            "cas_number": "70-30-4",
            "is_banned": True,
            "conditions": "Completely banned in cosmetics"
        },
        {
            "ingredient_name": "Chloroform",
            "inci_name": "Chloroform",
            "cas_number": "67-66-3",
            "is_banned": True,
            "conditions": "Prohibited in cosmetics"
        },
        {
            "ingredient_name": "Vinyl chloride",
            "inci_name": "Vinyl chloride",
            "cas_number": "75-01-4",
            "is_banned": True,
            "conditions": "Prohibited in cosmetics"
        },
        {
            "ingredient_name": "Zirconium salts",
            "inci_name": "Zirconium compounds",
            "is_banned": True,
            "conditions": "Prohibited in aerosol cosmetics"
        },
        {
            "ingredient_name": "Methylene chloride",
            "inci_name": "Methylene chloride",
            "cas_number": "75-09-2",
            "is_banned": True,
            "conditions": "Prohibited in cosmetics"
        },
        {
            "ingredient_name": "Formaldehyde",
            "inci_name": "Formaldehyde",
            "cas_number": "50-00-0",
            "max_concentration": 0.2,
            "is_banned": False,
            "conditions": "Maximum 0.2% as preservative, must be declared if >0.05%"
        },
        {
            "ingredient_name": "Hydroquinone",
            "inci_name": "Hydroquinone",
            "cas_number": "123-31-9",
            "max_concentration": 2.0,
            "is_banned": False,
            "conditions": "Maximum 2% in skin bleaching products"
        }
    ]
    
    for ingredient_data in prohibited_ingredients:
        ingredient = ProhibitedIngredient(
            regulation_id=fda_regulation.id,
            **ingredient_data
        )
        db.add(ingredient)
    
    # Claim restrictions
    claim_restrictions = [
        {
            "claim_type": "medical_claims",
            "prohibited_terms": ["cure", "treat", "heal", "therapeutic", "medicine", "drug", "disease"],
            "required_substantiation": "Medical claims not permitted for cosmetics"
        },
        {
            "claim_type": "drug_claims",
            "prohibited_terms": ["FDA approved", "prescription strength", "medical grade"],
            "required_substantiation": "Drug-like claims require FDA approval"
        },
        {
            "claim_type": "structure_function",
            "prohibited_terms": ["anti-bacterial", "anti-viral", "prevents infection"],
            "required_substantiation": "Structure/function claims require substantiation"
        }
    ]
    
    for claim_data in claim_restrictions:
        claim = ClaimRestriction(
            regulation_id=fda_regulation.id,
            **claim_data
        )
        db.add(claim)

def seed_eu_regulations(db: Session):
    """Seed EU cosmetics regulations."""
    
    # Create EU regulation
    eu_regulation = Regulation(
        jurisdiction="EU",
        regulation_name="EU Cosmetics Regulation (EC) No 1223/2009",
        effective_date=datetime(2013, 7, 11),
        category="cosmetics",
        document_path="https://ec.europa.eu/growth/sectors/cosmetics/legislation_en"
    )
    db.add(eu_regulation)
    db.flush()
    
    # EU prohibited ingredients (more restrictive than US)
    prohibited_ingredients = [
        {
            "ingredient_name": "Parabens (certain)",
            "inci_name": "Isopropylparaben, Isobutylparaben, Phenylparaben, Benzylparaben, Pentylparaben",
            "is_banned": True,
            "conditions": "These specific parabens are banned"
        },
        {
            "ingredient_name": "Formaldehyde",
            "inci_name": "Formaldehyde",
            "cas_number": "50-00-0",
            "max_concentration": 0.2,
            "is_banned": False,
            "conditions": "Maximum 0.2% as preservative, 0.1% in oral care products"
        },
        {
            "ingredient_name": "Triclosan",
            "inci_name": "Triclosan",
            "cas_number": "3380-34-5",
            "max_concentration": 0.3,
            "is_banned": False,
            "conditions": "Maximum 0.3% in specific applications"
        },
        {
            "ingredient_name": "Resorcinol",
            "inci_name": "Resorcinol",
            "cas_number": "108-46-3",
            "max_concentration": 0.5,
            "is_banned": False,
            "conditions": "Maximum 0.5% in hair dyes"
        },
        {
            "ingredient_name": "Lead compounds",
            "inci_name": "Lead compounds",
            "is_banned": True,
            "conditions": "All lead compounds prohibited"
        },
        {
            "ingredient_name": "Mercury compounds",
            "inci_name": "Mercury compounds",
            "is_banned": True,
            "conditions": "All mercury compounds prohibited except specific preservatives"
        }
    ]
    
    for ingredient_data in prohibited_ingredients:
        ingredient = ProhibitedIngredient(
            regulation_id=eu_regulation.id,
            **ingredient_data
        )
        db.add(ingredient)
    
    # EU claim restrictions
    claim_restrictions = [
        {
            "claim_type": "medical_claims",
            "prohibited_terms": ["cure", "treat", "heal", "therapeutic", "medicine", "drug"],
            "required_substantiation": "Medical claims not permitted for cosmetics"
        },
        {
            "claim_type": "misleading_claims",
            "prohibited_terms": ["hypoallergenic", "non-comedogenic", "dermatologically tested"],
            "required_substantiation": "Claims must be substantiated with appropriate testing"
        }
    ]
    
    for claim_data in claim_restrictions:
        claim = ClaimRestriction(
            regulation_id=eu_regulation.id,
            **claim_data
        )
        db.add(claim)

def seed_database():
    """Main function to seed the database."""
    
    # Create tables
    create_tables()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Check if data already exists
        existing_regulations = db.query(Regulation).count()
        
        if existing_regulations > 0:
            print("Database already seeded. Skipping...")
            return
        
        print("Seeding database with regulations...")
        
        # Seed US regulations
        seed_us_regulations(db)
        print("✓ US regulations seeded")
        
        # Seed EU regulations
        seed_eu_regulations(db)
        print("✓ EU regulations seeded")
        
        # Commit all changes
        db.commit()
        print("✓ Database seeding completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()