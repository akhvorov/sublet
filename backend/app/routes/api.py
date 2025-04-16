from fastapi import APIRouter, Depends, HTTPException, status
from ..utils.auth import verify_token
from ..utils.listings import load_listings
from typing import List, Dict, Any

router = APIRouter()

@router.get("/listings", response_model=List[Dict[str, Any]])
async def get_listings(token_data = Depends(verify_token)):
    """Получение списка всех объявлений"""
    _, _, listings = load_listings()
    return listings

@router.get("/listings/{listing_id}", response_model=Dict[str, Any])
async def get_listing(listing_id: int, token_data = Depends(verify_token)):
    """Получение информации о конкретном объявлении"""
    _, _, all_listings = load_listings()
    
    listing = next(
        (l for l in all_listings if l["id"] == listing_id),
        None
    )
    
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Объявление не найдено"
        )
    
    return listing 