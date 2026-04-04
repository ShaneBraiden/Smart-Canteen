"""
Food Validator Service - Validates and enriches OCR-scanned food items.

Uses the trained nutrition estimator model to:
1. Predict nutrition for unrecognized foods
2. Provide confidence scores
3. Validate against known database entries
"""
import re
import joblib
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from app.services.food_dataset import food_dataset, FoodItem, MatchResult


@dataclass
class ValidationResult:
    """Result of validating an OCR-scanned food item."""
    original_text: str
    cleaned_name: str
    source: str  # 'database', 'ml_prediction', 'hybrid'
    confidence: float
    
    # Nutrition data
    calories: float
    protein: float
    carbs: float
    fats: float
    
    # Database match info (if found)
    db_match: Optional[FoodItem] = None
    db_confidence: float = 0.0
    
    # ML prediction info
    ml_predicted: bool = False
    ml_confidence: float = 0.0
    
    # Alternatives from database
    alternatives: List[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'original_text': self.original_text,
            'cleaned_name': self.cleaned_name,
            'source': self.source,
            'confidence': round(self.confidence, 2),
            'nutrition': {
                'calories': round(self.calories, 1),
                'protein': round(self.protein, 1),
                'carbs': round(self.carbs, 1),
                'fats': round(self.fats, 1)
            },
            'database_match': self.db_match.to_dict() if self.db_match else None,
            'database_confidence': round(self.db_confidence, 2),
            'ml_predicted': self.ml_predicted,
            'ml_confidence': round(self.ml_confidence, 2),
            'alternatives': self.alternatives or []
        }


class FoodValidator:
    """
    Validates and enriches food items scanned by OCR.
    
    Workflow:
    1. Clean and normalize OCR text
    2. Try fuzzy matching against database
    3. If no good match, use ML model to predict nutrition
    4. Return combined result with confidence scores
    """
    
    # Thresholds
    DB_MATCH_THRESHOLD = 75  # Minimum fuzzy match score to trust database
    DB_HIGH_CONFIDENCE = 90  # Score for very confident database match
    ML_FALLBACK_CONFIDENCE = 0.7  # Default confidence for ML predictions
    
    def __init__(self):
        self.model = None
        self.model_path = Path(__file__).parent.parent / 'ml' / 'nutrition_estimator.joblib'
        self._loaded = False
    
    def _load_model(self):
        """Load the trained nutrition estimator model."""
        if self._loaded:
            return
        
        if self.model_path.exists():
            try:
                data = joblib.load(self.model_path)
                self.model = data['pipeline']
                self.target_cols = data.get('target_cols', ['Calories', 'Protein', 'Carbs', 'Fats'])
                self._loaded = True
                print(f"Loaded nutrition estimator model from {self.model_path}")
            except Exception as e:
                print(f"Error loading nutrition estimator model: {e}")
                self.model = None
        else:
            print(f"Nutrition estimator model not found at {self.model_path}")
    
    def _clean_food_name(self, text: str) -> str:
        """Clean and normalize OCR text for matching."""
        if not text:
            return ''
        
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove common OCR artifacts
        text = re.sub(r'[^\w\s\-()]', '', text)
        
        # Remove quantity indicators like "(2 pcs)", "(100g)", etc.
        text = re.sub(r'\s*\(\d+\s*pcs?\)', '', text)
        text = re.sub(r'\s*\(\d+\s*g\)', '', text)
        text = re.sub(r'\s*\(\d+\s*ml\)', '', text)
        text = re.sub(r'\s*x\s*\d+', '', text)  # "x2", "x 3"
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _enhanced_fuzzy_match(self, query: str) -> MatchResult:
        """
        Enhanced fuzzy matching that handles partial matches better.
        
        Tries multiple matching strategies:
        1. Direct fuzzy match
        2. Match with common suffixes added
        3. Match with query as substring
        """
        food_dataset.ensure_loaded()
        
        # Strategy 1: Direct match
        direct_match = food_dataset.fuzzy_match(query, threshold=self.DB_MATCH_THRESHOLD)
        
        if direct_match.matched_item and direct_match.confidence >= (self.DB_HIGH_CONFIDENCE / 100):
            return direct_match
        
        # Strategy 2: Try with common suffixes
        suffixes = ['(2 pcs)', '(plate)', '(bowl)', '(cup)', '(glass)']
        best_suffix_match = None
        best_suffix_score = 0
        
        for suffix in suffixes:
            test_query = f"{query} {suffix}"
            match = food_dataset.fuzzy_match(test_query, threshold=60)
            if match.matched_item and match.confidence > best_suffix_score:
                best_suffix_score = match.confidence
                best_suffix_match = match
        
        # Strategy 3: Check if query is contained in any item name
        query_lower = query.lower()
        for item_name in food_dataset.item_names:
            item_lower = item_name.lower()
            # Check if query is a substantial part of the item name
            if query_lower in item_lower:
                # Calculate confidence based on how much of the name matches
                coverage = len(query_lower) / len(item_lower)
                if coverage >= 0.3:  # At least 30% coverage
                    item = food_dataset.get_item(item_name)
                    if item:
                        substring_confidence = 0.7 + (coverage * 0.25)  # 70-95% confidence
                        if not best_suffix_match or substring_confidence > best_suffix_score:
                            return MatchResult(
                                query=query,
                                matched_item=item,
                                confidence=substring_confidence,
                                alternatives=direct_match.alternatives
                            )
        
        # Return best available match
        if best_suffix_match and best_suffix_score > direct_match.confidence:
            return best_suffix_match
        
        return direct_match
    
    def _predict_nutrition(self, food_name: str) -> Dict[str, float]:
        """Use ML model to predict nutrition from food name."""
        self._load_model()
        
        if self.model is None:
            # Return defaults if model not available
            return {'calories': 200, 'protein': 5, 'carbs': 30, 'fats': 8}
        
        try:
            prediction = self.model.predict([food_name])[0]
            return {
                'calories': max(0, prediction[0]),
                'protein': max(0, prediction[1]),
                'carbs': max(0, prediction[2]),
                'fats': max(0, prediction[3])
            }
        except Exception as e:
            print(f"ML prediction error: {e}")
            return {'calories': 200, 'protein': 5, 'carbs': 30, 'fats': 8}
    
    def _calculate_ml_confidence(self, food_name: str, prediction: Dict[str, float]) -> float:
        """
        Calculate confidence score for ML prediction.
        
        Higher confidence if:
        - Food name contains common Indian food keywords
        - Predicted values are in reasonable ranges
        """
        confidence = 0.6  # Base confidence
        
        # Boost for common keywords
        indian_keywords = [
            'dosa', 'idli', 'biryani', 'curry', 'masala', 'dal', 'roti', 'naan',
            'paneer', 'chicken', 'rice', 'paratha', 'samosa', 'pakora', 'vada',
            'tea', 'coffee', 'lassi', 'chutney', 'raita', 'pulao', 'korma'
        ]
        if any(kw in food_name.lower() for kw in indian_keywords):
            confidence += 0.15
        
        # Check if values are in reasonable ranges
        if 50 <= prediction['calories'] <= 800:
            confidence += 0.05
        if 0 <= prediction['protein'] <= 50:
            confidence += 0.05
        if 0 <= prediction['carbs'] <= 100:
            confidence += 0.05
        if 0 <= prediction['fats'] <= 50:
            confidence += 0.05
        
        return min(confidence, 0.95)  # Cap at 95%
    
    def validate(self, food_text: str) -> ValidationResult:
        """
        Validate and enrich a single food item from OCR.
        
        Args:
            food_text: Raw text from OCR
            
        Returns:
            ValidationResult with nutrition and confidence
        """
        # Clean the input
        cleaned_name = self._clean_food_name(food_text)
        
        if not cleaned_name:
            return ValidationResult(
                original_text=food_text,
                cleaned_name='',
                source='none',
                confidence=0,
                calories=0,
                protein=0,
                carbs=0,
                fats=0
            )
        
        # Try enhanced database fuzzy match
        food_dataset.ensure_loaded()
        match_result: MatchResult = self._enhanced_fuzzy_match(cleaned_name)
        
        # Prepare alternatives
        alternatives = []
        for alt_name, alt_score in (match_result.alternatives or [])[:3]:
            alt_item = food_dataset.get_item(alt_name)
            if alt_item:
                alternatives.append({
                    'name': alt_item.name,
                    'match_score': alt_score,
                    'calories': alt_item.calories,
                    'protein': alt_item.protein
                })
        
        # Case 1: High confidence database match
        if match_result.matched_item and match_result.confidence >= (self.DB_HIGH_CONFIDENCE / 100):
            item = match_result.matched_item
            return ValidationResult(
                original_text=food_text,
                cleaned_name=cleaned_name,
                source='database',
                confidence=match_result.confidence,
                calories=item.calories,
                protein=item.protein,
                carbs=item.carbs,
                fats=item.fats,
                db_match=item,
                db_confidence=match_result.confidence,
                ml_predicted=False,
                alternatives=alternatives
            )
        
        # Case 2: Moderate database match - use hybrid approach
        if match_result.matched_item and match_result.confidence >= (self.DB_MATCH_THRESHOLD / 100):
            item = match_result.matched_item
            
            # Also get ML prediction for comparison
            ml_pred = self._predict_nutrition(cleaned_name)
            ml_conf = self._calculate_ml_confidence(cleaned_name, ml_pred)
            
            # Weight towards database match if confidence is decent
            db_weight = match_result.confidence
            ml_weight = 1 - db_weight
            
            return ValidationResult(
                original_text=food_text,
                cleaned_name=cleaned_name,
                source='hybrid',
                confidence=match_result.confidence,
                calories=item.calories * db_weight + ml_pred['calories'] * ml_weight,
                protein=item.protein * db_weight + ml_pred['protein'] * ml_weight,
                carbs=item.carbs * db_weight + ml_pred['carbs'] * ml_weight,
                fats=item.fats * db_weight + ml_pred['fats'] * ml_weight,
                db_match=item,
                db_confidence=match_result.confidence,
                ml_predicted=True,
                ml_confidence=ml_conf,
                alternatives=alternatives
            )
        
        # Case 3: No good database match - use ML prediction
        ml_pred = self._predict_nutrition(cleaned_name)
        ml_conf = self._calculate_ml_confidence(cleaned_name, ml_pred)
        
        return ValidationResult(
            original_text=food_text,
            cleaned_name=cleaned_name,
            source='ml_prediction',
            confidence=ml_conf,
            calories=ml_pred['calories'],
            protein=ml_pred['protein'],
            carbs=ml_pred['carbs'],
            fats=ml_pred['fats'],
            db_match=None,
            db_confidence=match_result.confidence if match_result else 0,
            ml_predicted=True,
            ml_confidence=ml_conf,
            alternatives=alternatives
        )
    
    def validate_batch(self, food_texts: List[str]) -> List[ValidationResult]:
        """
        Validate multiple food items at once.
        
        Args:
            food_texts: List of raw texts from OCR
            
        Returns:
            List of ValidationResult objects
        """
        return [self.validate(text) for text in food_texts]
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get status of the ML model."""
        self._load_model()
        
        return {
            'model_loaded': self._loaded,
            'model_path': str(self.model_path),
            'model_exists': self.model_path.exists()
        }


# Singleton instance
food_validator = FoodValidator()
