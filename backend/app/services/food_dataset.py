import pandas as pd
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from rapidfuzz import fuzz, process

from app.core.config import settings


@dataclass
class FoodItem:
    """Represents a food item from the dataset."""
    name: str
    calories: float
    protein: float
    carbs: float
    fats: float
    is_veg: bool
    allergens: List[str]
    price: float
    category: str
    cuisine: str
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'calories': self.calories,
            'protein': self.protein,
            'carbs': self.carbs,
            'fats': self.fats,
            'is_veg': self.is_veg,
            'allergens': self.allergens,
            'price': self.price,
            'category': self.category,
            'cuisine': self.cuisine
        }
    
    @property
    def nutritional_density(self) -> float:
        """Calculate nutritional value per rupee."""
        if self.price <= 0:
            return 0
        # Simple score: (protein * 2 + fiber approximation) / price
        return (self.protein * 2 + self.carbs * 0.1) / self.price


@dataclass
class MatchResult:
    """Result of fuzzy matching a menu item to dataset."""
    query: str
    matched_item: Optional[FoodItem]
    confidence: float
    alternatives: List[tuple]  # [(name, score), ...]


class FoodDataset:
    """
    Service for loading and querying the Indian food composition dataset.
    """
    
    @staticmethod
    def _extract_match_tuples(matches) -> List[tuple]:
        """
        Normalize `rapidfuzz.process.extract` output.
        Returns list of (name, score) tuples.
        """
        normalized = []
        for match in matches:
            if len(match) >= 2:
                normalized.append((match[0], match[1]))
        return normalized

    def __init__(self, dataset_path: Optional[str] = None):
        self.dataset_path = dataset_path or settings.FOOD_DATASET_PATH
        self.df: Optional[pd.DataFrame] = None
        self.items: Dict[str, FoodItem] = {}
        self.item_names: List[str] = []
        self._loaded = False
    
    def load(self) -> bool:
        """Load dataset from CSV file."""
        try:
            # Handle relative path from backend directory
            path = Path(self.dataset_path)
            if not path.is_absolute():
                # Try relative to backend directory
                backend_dir = Path(__file__).parent.parent.parent
                path = backend_dir.parent / self.dataset_path
            
            self.df = pd.read_csv(path)
            self._process_dataset()
            self._loaded = True
            print(f"Loaded {len(self.items)} food items from dataset")
            return True
        except Exception as e:
            print(f"Error loading dataset: {e}")
            return False
    
    def _process_dataset(self):
        """Process DataFrame into FoodItem objects."""
        for _, row in self.df.iterrows():
            # Parse allergens
            allergens_str = str(row.get('Common_Allergens', 'None'))
            if allergens_str.lower() == 'none' or pd.isna(row.get('Common_Allergens')):
                allergens = []
            else:
                allergens = [a.strip().lower() for a in allergens_str.split()]
            
            # Parse is_veg
            is_veg_val = row.get('Is_Veg', 'Yes')
            is_veg = str(is_veg_val).lower() in ('yes', 'true', '1', 'veg')
            
            item = FoodItem(
                name=str(row['Food_Item']),
                calories=float(row.get('Calories', 0)),
                protein=float(row.get('Protein', 0)),
                carbs=float(row.get('Carbs', 0)),
                fats=float(row.get('Fats', 0)),
                is_veg=is_veg,
                allergens=allergens,
                price=float(row.get('Price', 0)),
                category=str(row.get('Category', 'Unknown')),
                cuisine=str(row.get('Cuisine', 'Unknown'))
            )
            
            # Store with lowercase key for matching
            key = item.name.lower()
            self.items[key] = item
            self.item_names.append(item.name)
    
    def ensure_loaded(self):
        """Ensure dataset is loaded."""
        if not self._loaded:
            self.load()
    
    def get_item(self, name: str) -> Optional[FoodItem]:
        """Get exact match for food item."""
        self.ensure_loaded()
        return self.items.get(name.lower())
    
    def fuzzy_match(self, query: str, threshold: int = 70) -> MatchResult:
        """
        Find best matching food item using fuzzy string matching.
        
        Args:
            query: Search query (dish name from OCR)
            threshold: Minimum match score (0-100)
            
        Returns:
            MatchResult with best match and alternatives
        """
        self.ensure_loaded()
        
        if not query or not self.item_names:
            return MatchResult(query=query, matched_item=None, confidence=0, alternatives=[])
        
        # Get top 5 matches
        matches = process.extract(query, self.item_names, scorer=fuzz.token_sort_ratio, limit=5)
        matches = self._extract_match_tuples(matches)
        
        if not matches:
            return MatchResult(query=query, matched_item=None, confidence=0, alternatives=[])
        
        best_match, best_score = matches[0]
        
        if best_score >= threshold:
            matched_item = self.items.get(best_match.lower())
            confidence = best_score / 100.0
        else:
            matched_item = None
            confidence = best_score / 100.0
        
        # Format alternatives
        alternatives = [(name, score) for name, score in matches[1:] if score >= threshold - 20]
        
        return MatchResult(
            query=query,
            matched_item=matched_item,
            confidence=confidence,
            alternatives=alternatives
        )
    
    def search(self, query: str, limit: int = 10) -> List[FoodItem]:
        """
        Search for food items matching query.
        
        Args:
            query: Search term
            limit: Maximum results
            
        Returns:
            List of matching FoodItem objects
        """
        self.ensure_loaded()
        
        matches = process.extract(query, self.item_names, scorer=fuzz.token_sort_ratio, limit=limit)
        matches = self._extract_match_tuples(matches)
        
        results = []
        for name, score in matches:
            if score >= 50:
                item = self.items.get(name.lower())
                if item:
                    results.append(item)
        
        return results
    
    def get_by_category(self, category: str) -> List[FoodItem]:
        """Get all items in a category."""
        self.ensure_loaded()
        return [item for item in self.items.values() 
                if item.category.lower() == category.lower()]
    
    def get_by_cuisine(self, cuisine: str) -> List[FoodItem]:
        """Get all items of a cuisine type."""
        self.ensure_loaded()
        return [item for item in self.items.values() 
                if item.cuisine.lower() == cuisine.lower()]
    
    def get_vegetarian(self) -> List[FoodItem]:
        """Get all vegetarian items."""
        self.ensure_loaded()
        return [item for item in self.items.values() if item.is_veg]
    
    def get_non_vegetarian(self) -> List[FoodItem]:
        """Get all non-vegetarian items."""
        self.ensure_loaded()
        return [item for item in self.items.values() if not item.is_veg]
    
    def filter_allergens(self, items: List[FoodItem], exclude_allergens: List[str]) -> List[FoodItem]:
        """Filter out items containing specified allergens."""
        exclude_set = {a.lower() for a in exclude_allergens}
        return [item for item in items 
                if not any(allergen in exclude_set for allergen in item.allergens)]
    
    def get_items_in_budget(self, max_price: float, is_veg: Optional[bool] = None) -> List[FoodItem]:
        """Get items within budget, optionally filtered by veg/non-veg."""
        self.ensure_loaded()
        
        items = [item for item in self.items.values() if item.price <= max_price]
        
        if is_veg is not None:
            items = [item for item in items if item.is_veg == is_veg]
        
        return sorted(items, key=lambda x: x.nutritional_density, reverse=True)
    
    def get_substitutes(self, item: FoodItem, max_price: Optional[float] = None) -> List[FoodItem]:
        """
        Find substitute items with similar nutrition but potentially lower price.
        
        Args:
            item: Original food item
            max_price: Maximum price for substitute
            
        Returns:
            List of substitute options
        """
        self.ensure_loaded()
        
        max_price = max_price or item.price
        same_veg = item.is_veg
        same_category = item.category
        
        candidates = []
        for candidate in self.items.values():
            if candidate.name == item.name:
                continue
            if candidate.is_veg != same_veg:
                continue
            if candidate.price > max_price:
                continue
            
            # Calculate similarity in macros
            protein_diff = abs(candidate.protein - item.protein) / max(item.protein, 1)
            carb_diff = abs(candidate.carbs - item.carbs) / max(item.carbs, 1)
            calorie_diff = abs(candidate.calories - item.calories) / max(item.calories, 1)
            
            similarity = 1 - (protein_diff + carb_diff + calorie_diff) / 3
            
            if similarity > 0.5:  # At least 50% similar
                candidates.append((candidate, similarity, item.price - candidate.price))
        
        # Sort by savings and similarity
        candidates.sort(key=lambda x: (x[2], x[1]), reverse=True)
        
        return [c[0] for c in candidates[:5]]
    
    def get_all_items(self) -> List[FoodItem]:
        """Get all food items."""
        self.ensure_loaded()
        return list(self.items.values())
    
    def get_stats(self) -> dict:
        """Get dataset statistics."""
        self.ensure_loaded()
        
        items = list(self.items.values())
        veg_count = len([i for i in items if i.is_veg])
        
        return {
            'total_items': len(items),
            'vegetarian': veg_count,
            'non_vegetarian': len(items) - veg_count,
            'categories': list(set(i.category for i in items)),
            'cuisines': list(set(i.cuisine for i in items)),
            'price_range': {
                'min': min(i.price for i in items) if items else 0,
                'max': max(i.price for i in items) if items else 0,
                'avg': sum(i.price for i in items) / len(items) if items else 0
            },
            'calorie_range': {
                'min': min(i.calories for i in items) if items else 0,
                'max': max(i.calories for i in items) if items else 0
            }
        }


# Singleton instance
food_dataset = FoodDataset()
