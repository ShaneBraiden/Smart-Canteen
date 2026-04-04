"""
Scanned Menu Model - Stores OCR-extracted menu items per user.

Each user can have multiple named menus (e.g., "College Canteen", "Office Cafe").
Menu items are validated by ML model before storage.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, ClassVar
from pydantic import BaseModel, Field
from bson import ObjectId


class ScannedFoodItem(BaseModel):
    """A food item extracted from OCR and validated by ML."""
    name: str
    cleaned_name: str
    
    # Extracted from OCR
    extracted_price: Optional[float] = None
    
    # ML-validated nutrition
    calories: float
    protein: float
    carbs: float
    fats: float
    
    # Metadata
    is_veg: bool = True
    category: str = "Lunch"
    
    # Validation info
    validation_source: str  # 'database', 'hybrid', 'ml_prediction'
    confidence: float
    database_match: Optional[str] = None  # Name of matched DB item
    
    # Timestamps
    added_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'cleaned_name': self.cleaned_name,
            'extracted_price': self.extracted_price,
            'calories': self.calories,
            'protein': self.protein,
            'carbs': self.carbs,
            'fats': self.fats,
            'is_veg': self.is_veg,
            'category': self.category,
            'validation_source': self.validation_source,
            'confidence': self.confidence,
            'database_match': self.database_match,
            'added_at': self.added_at.isoformat() if isinstance(self.added_at, datetime) else self.added_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScannedFoodItem':
        if 'added_at' in data and isinstance(data['added_at'], str):
            data['added_at'] = datetime.fromisoformat(data['added_at'])
        return cls(**data)
    
    @property
    def price(self) -> float:
        """Get price - use extracted or estimate."""
        if self.extracted_price and self.extracted_price > 0:
            return self.extracted_price
        # Estimate based on calories
        return max(20, min(150, self.calories * 0.15))
    
    @property
    def nutritional_density(self) -> float:
        """Nutritional value per rupee."""
        if self.price <= 0:
            return 0
        return (self.protein * 2 + self.carbs * 0.1) / self.price


class ScannedMenu(BaseModel):
    """A named scanned menu stored in MongoDB."""
    COLLECTION: ClassVar[str] = "scanned_menus"
    
    id: Optional[str] = None
    user_id: str
    
    # Menu identification
    name: str = "Untitled Menu"  # User-given name like "College Canteen"
    
    # Menu items
    items: List[ScannedFoodItem] = Field(default_factory=list)
    
    # Metadata
    last_scan_at: Optional[datetime] = None
    total_items: int = 0
    ml_predictions_count: int = 0
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'name': self.name,
            'items': [item.to_dict() for item in self.items],
            'last_scan_at': self.last_scan_at.isoformat() if self.last_scan_at else None,
            'total_items': len(self.items),
            'ml_predictions_count': sum(1 for i in self.items if i.validation_source == 'ml_prediction'),
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        }
    
    def to_summary(self) -> Dict[str, Any]:
        """Return a summary without full item list (for history view)."""
        veg_count = sum(1 for i in self.items if i.is_veg)
        return {
            'id': self.id,
            'name': self.name,
            'total_items': len(self.items),
            'veg_items': veg_count,
            'non_veg_items': len(self.items) - veg_count,
            'ml_predictions_count': sum(1 for i in self.items if i.validation_source == 'ml_prediction'),
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScannedMenu':
        if not data:
            return None
        
        # Parse items
        items = []
        for item_data in data.get('items', []):
            items.append(ScannedFoodItem.from_dict(item_data))
        
        # Parse dates
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        
        last_scan_at = data.get('last_scan_at')
        if isinstance(last_scan_at, str):
            last_scan_at = datetime.fromisoformat(last_scan_at)
        
        return cls(
            id=str(data.get('_id', '')),
            user_id=data.get('user_id', ''),
            name=data.get('name', 'Untitled Menu'),
            items=items,
            last_scan_at=last_scan_at,
            total_items=len(items),
            ml_predictions_count=sum(1 for i in items if i.validation_source == 'ml_prediction'),
            created_at=created_at or datetime.utcnow(),
            updated_at=updated_at or datetime.utcnow()
        )
