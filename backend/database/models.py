from sqlalchemy import Column, String, Text, Numeric, DateTime, Boolean, ForeignKey, JSON, ARRAY
#from decimal import Decimal
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

Base = declarative_base()

class Regulation(Base):
    __tablename__ = "regulations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jurisdiction = Column(String(100), nullable=False)
    regulation_name = Column(Text, nullable=False)
    effective_date = Column(DateTime)
    category = Column(String(100))
    document_path = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    prohibited_ingredients = relationship("ProhibitedIngredient", back_populates="regulation")
    claim_restrictions = relationship("ClaimRestriction", back_populates="regulation")

class ProhibitedIngredient(Base):
    __tablename__ = "prohibited_ingredients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    regulation_id = Column(UUID(as_uuid=True), ForeignKey("regulations.id"))
    ingredient_name = Column(Text, nullable=False)
    inci_name = Column(Text)
    cas_number = Column(String(50))
    max_concentration = Column(Numeric(10, 6))
    conditions = Column(Text)
    is_banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    regulation = relationship("Regulation", back_populates="prohibited_ingredients")

class ClaimRestriction(Base):
    __tablename__ = "claim_restrictions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    regulation_id = Column(UUID(as_uuid=True), ForeignKey("regulations.id"))
    claim_type = Column(String(100), nullable=False)
    prohibited_terms = Column(ARRAY(String))
    required_substantiation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    regulation = relationship("Regulation", back_populates="claim_restrictions")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    brand = Column(String(255))
    category = Column(String(100))
    target_demographic = Column(String(100))
    usage_instructions = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ingredients = relationship("ProductIngredient", back_populates="product")
    documents = relationship("ProductDocument", back_populates="product")
    compliance_analyses = relationship("ComplianceAnalysis", back_populates="product")

class ProductIngredient(Base):
    __tablename__ = "product_ingredients"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    ingredient_name = Column(String(255), nullable=False)
    inci_name = Column(String(255))
    cas_number = Column(String(50))
    concentration = Column(Numeric(10, 6))
    function = Column(String(100))  # preservative, colorant, etc.
    is_allergen = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="ingredients")

class ProductDocument(Base):
    __tablename__ = "product_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    document_type = Column(String(100), nullable=False)  # ingredient_list, product_label, etc.
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(255))
    extracted_text = Column(Text)
    document_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="documents")

class ComplianceAnalysis(Base):
    __tablename__ = "compliance_analyses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    jurisdiction = Column(String(100), nullable=False)
    overall_status = Column(String(50), nullable=False)  # compliant, non_compliant, warning
    analysis_results = Column(JSON)
    recommendations = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="compliance_analyses")
    violations = relationship("ComplianceViolation", back_populates="analysis")

class ComplianceViolation(Base):
    __tablename__ = "compliance_violations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("compliance_analyses.id"))
    violation_type = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=False)  # high, medium, low
    description = Column(Text, nullable=False)
    regulatory_reference = Column(String(500))
    suggested_action = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    analysis = relationship("ComplianceAnalysis", back_populates="violations")

class DocumentProcessingJob(Base):
    __tablename__ = "document_processing_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_path = Column(String(500), nullable=False)
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    document_type = Column(String(100))
    extracted_data = Column(JSON)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)