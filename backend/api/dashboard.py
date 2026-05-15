from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database.database import get_db
from database.models import (
    Product, ProductDocument, ComplianceAnalysis, 
    ComplianceViolation, DocumentProcessingJob
)
from datetime import datetime, timedelta
from typing import List, Dict

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Get dashboard statistics and recent analyses.
    """
    try:
        # Get basic statistics
        total_documents = db.query(ProductDocument).count()
        total_products = db.query(Product).count()
        total_analyses = db.query(ComplianceAnalysis).count()
        
        # Get compliance status distribution
        compliance_stats = db.query(
            ComplianceAnalysis.overall_status,
            func.count(ComplianceAnalysis.id).label('count')
        ).group_by(ComplianceAnalysis.overall_status).all()
        
        # Convert to dictionary
        status_counts = {status: count for status, count in compliance_stats}
        
        # Get violation statistics
        violation_stats = db.query(
            ComplianceViolation.severity,
            func.count(ComplianceViolation.id).label('count')
        ).group_by(ComplianceViolation.severity).all()
        
        violation_counts = {severity: count for severity, count in violation_stats}
        
        # Get recent analyses (last 10)
        recent_analyses = db.query(
            ComplianceAnalysis,
            Product.name.label('product_name')
        ).join(
            Product, ComplianceAnalysis.product_id == Product.id
        ).order_by(
            desc(ComplianceAnalysis.created_at)
        ).limit(10).all()
        
        recent_analyses_data = []
        for analysis, product_name in recent_analyses:
            recent_analyses_data.append({
                "id": str(analysis.id),
                "product_name": product_name or "Unknown Product",
                "status": analysis.overall_status,
                "jurisdiction": analysis.jurisdiction,
                "timestamp": analysis.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        # Get processing job statistics
        job_stats = db.query(
            DocumentProcessingJob.status,
            func.count(DocumentProcessingJob.id).label('count')
        ).group_by(DocumentProcessingJob.status).all()
        
        job_counts = {status: count for status, count in job_stats}
        
        return {
            "stats": {
                "total_documents": total_documents,
                "total_products": total_products,
                "total_analyses": total_analyses,
                "compliant_products": status_counts.get('compliant', 0),
                "non_compliant_products": status_counts.get('non_compliant', 0),
                "warnings": status_counts.get('warning', 0),
                "violations": violation_counts.get('high', 0) + violation_counts.get('medium', 0),
                "high_severity_violations": violation_counts.get('high', 0),
                "medium_severity_violations": violation_counts.get('medium', 0),
                "low_severity_violations": violation_counts.get('low', 0)
            },
            "recent_analyses": recent_analyses_data,
            "processing_jobs": job_counts,
            "compliance_distribution": [
                {"status": "compliant", "count": status_counts.get('compliant', 0)},
                {"status": "warning", "count": status_counts.get('warning', 0)},
                {"status": "non_compliant", "count": status_counts.get('non_compliant', 0)}
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(e)}")

@router.get("/trends")
async def get_compliance_trends(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get compliance trends over time.
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get daily compliance analysis counts
        daily_stats = db.query(
            func.date(ComplianceAnalysis.created_at).label('date'),
            ComplianceAnalysis.overall_status,
            func.count(ComplianceAnalysis.id).label('count')
        ).filter(
            ComplianceAnalysis.created_at >= start_date
        ).group_by(
            func.date(ComplianceAnalysis.created_at),
            ComplianceAnalysis.overall_status
        ).order_by(
            func.date(ComplianceAnalysis.created_at)
        ).all()
        
        # Format data for charts
        trends_data = {}
        for date, status, count in daily_stats:
            date_str = date.strftime("%Y-%m-%d")
            if date_str not in trends_data:
                trends_data[date_str] = {
                    "date": date_str,
                    "compliant": 0,
                    "warning": 0,
                    "non_compliant": 0
                }
            trends_data[date_str][status] = count
        
        return {
            "trends": list(trends_data.values()),
            "period_days": days
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trends: {str(e)}")

@router.get("/violations/summary")
async def get_violation_summary(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get summary of most common violations.
    """
    try:
        # Get most common violation types
        violation_types = db.query(
            ComplianceViolation.violation_type,
            func.count(ComplianceViolation.id).label('count')
        ).group_by(
            ComplianceViolation.violation_type
        ).order_by(
            desc(func.count(ComplianceViolation.id))
        ).limit(limit).all()
        
        # Get recent violations with details
        recent_violations = db.query(
            ComplianceViolation,
            Product.name.label('product_name')
        ).join(
            ComplianceAnalysis, ComplianceViolation.analysis_id == ComplianceAnalysis.id
        ).join(
            Product, ComplianceAnalysis.product_id == Product.id
        ).order_by(
            desc(ComplianceViolation.created_at)
        ).limit(limit).all()
        
        recent_violations_data = []
        for violation, product_name in recent_violations:
            recent_violations_data.append({
                "id": str(violation.id),
                "product_name": product_name or "Unknown Product",
                "violation_type": violation.violation_type,
                "severity": violation.severity,
                "description": violation.description,
                "timestamp": violation.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return {
            "common_violations": [
                {"type": vtype, "count": count}
                for vtype, count in violation_types
            ],
            "recent_violations": recent_violations_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get violation summary: {str(e)}")

@router.get("/jurisdiction-stats")
async def get_jurisdiction_stats(db: Session = Depends(get_db)):
    """
    Get compliance statistics by jurisdiction.
    """
    try:
        # Get analysis counts by jurisdiction
        jurisdiction_stats = db.query(
            ComplianceAnalysis.jurisdiction,
            ComplianceAnalysis.overall_status,
            func.count(ComplianceAnalysis.id).label('count')
        ).group_by(
            ComplianceAnalysis.jurisdiction,
            ComplianceAnalysis.overall_status
        ).order_by(
            ComplianceAnalysis.jurisdiction
        ).all()
        
        # Format data by jurisdiction
        jurisdiction_data = {}
        for jurisdiction, status, count in jurisdiction_stats:
            if jurisdiction not in jurisdiction_data:
                jurisdiction_data[jurisdiction] = {
                    "jurisdiction": jurisdiction,
                    "compliant": 0,
                    "warning": 0,
                    "non_compliant": 0,
                    "total": 0
                }
            jurisdiction_data[jurisdiction][status] = count
            jurisdiction_data[jurisdiction]["total"] += count
        
        return {
            "jurisdiction_stats": list(jurisdiction_data.values())
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get jurisdiction stats: {str(e)}")

@router.get("/activity")
async def get_recent_activity(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get recent system activity.
    """
    try:
        # Get recent document uploads
        recent_documents = db.query(
            ProductDocument.original_filename,
            ProductDocument.document_type,
            ProductDocument.created_at,
            Product.name.label('product_name')
        ).join(
            Product, ProductDocument.product_id == Product.id, isouter=True
        ).order_by(
            desc(ProductDocument.created_at)
        ).limit(limit//2).all()
        
        # Get recent analyses
        recent_analyses = db.query(
            ComplianceAnalysis.overall_status,
            ComplianceAnalysis.jurisdiction,
            ComplianceAnalysis.created_at,
            Product.name.label('product_name')
        ).join(
            Product, ComplianceAnalysis.product_id == Product.id
        ).order_by(
            desc(ComplianceAnalysis.created_at)
        ).limit(limit//2).all()
        
        # Combine and format activities
        activities = []
        
        for doc in recent_documents:
            activities.append({
                "type": "document_upload",
                "description": f"Uploaded {doc.document_type}: {doc.original_filename}",
                "product_name": doc.product_name,
                "timestamp": doc.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        for analysis in recent_analyses:
            activities.append({
                "type": "compliance_analysis",
                "description": f"Compliance analysis completed - {analysis.overall_status}",
                "product_name": analysis.product_name,
                "jurisdiction": analysis.jurisdiction,
                "timestamp": analysis.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        # Sort by timestamp
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "activities": activities[:limit]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent activity: {str(e)}")