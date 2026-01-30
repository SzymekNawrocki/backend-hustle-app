from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict
from app.database import get_db
from app.models.finance import Asset, AssetType
from app.schemas.finance import AssetCreate, AssetResponse

router = APIRouter(prefix="/finance", tags=["Finance"])

@router.post("/assets", response_model=AssetResponse)
def create_asset(asset: AssetCreate, db: Session = Depends(get_db)):
    """
    Adds a new asset to the portfolio.
    """
    db_asset = Asset(**asset.model_dump())
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset

@router.get("/assets", response_model=List[AssetResponse])
def list_assets(db: Session = Depends(get_db)):
    """
    Returns a list of all assets in the portfolio.
    """
    return db.query(Asset).all()

@router.get("/portfolio-summary")
def get_portfolio_summary(db: Session = Depends(get_db)):
    """
    Analytical endpoint returning total net worth and percentage distribution.
    Calculations are based on the purchase price.
    """
    assets = db.query(Asset).all()
    
    if not assets:
        return {
            "total_net_worth": 0.0,
            "distribution": {}
        }
    
    total_net_worth = sum(asset.amount * asset.buy_price for asset in assets)
    
    # Calculate distribution by asset type
    distribution = {}
    for a_type in AssetType:
        type_sum = sum(
            asset.amount * asset.buy_price 
            for asset in assets if asset.asset_type == a_type
        )
        if type_sum > 0:
            percentage = (type_sum / total_net_worth) * 100
            distribution[a_type.value] = {
                "total_value": round(type_sum, 2),
                "percentage": round(percentage, 2)
            }
            
    return {
        "total_net_worth": round(total_net_worth, 2),
        "distribution": distribution
    }
