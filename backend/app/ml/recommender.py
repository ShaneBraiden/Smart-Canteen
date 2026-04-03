import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import pickle
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
import pandas as pd

from app.services.food_dataset import FoodItem, food_dataset
from app.models.user import User, Goal, DietType, ActivityLevel


@dataclass
class UserFeedback:
    """User feedback on a meal recommendation."""
    user_id: str
    food_item_name: str
    rating: int  # 1-5
    meal_slot: str
    timestamp: datetime
    was_consumed: bool


@dataclass
class UserFeatures:
    """Feature vector for a user."""
    age: float
    gender_encoded: int
    bmi: float
    activity_encoded: int
    goal_encoded: int
    diet_type_encoded: int
    daily_budget: float
    target_calories: float


@dataclass
class FoodFeatures:
    """Feature vector for a food item."""
    calories: float
    protein: float
    carbs: float
    fats: float
    price: float
    is_veg: int
    category_encoded: int
    cuisine_encoded: int


class FeatureEncoder:
    """Encode categorical features for ML models."""
    
    def __init__(self):
        self.gender_encoder = {'male': 0, 'female': 1, 'other': 2}
        self.activity_encoder = {
            'sedentary': 0, 'light': 1, 'moderate': 2, 'active': 3, 'very_active': 4
        }
        self.goal_encoder = {'weight_loss': 0, 'maintenance': 1, 'weight_gain': 2}
        self.diet_encoder = {'veg': 0, 'non_veg': 1, 'vegan': 2, 'eggetarian': 3}
        
        self.category_encoder = LabelEncoder()
        self.cuisine_encoder = LabelEncoder()
        self.scaler = StandardScaler()
        
        self._fitted = False
    
    def fit(self, food_items: List[FoodItem]):
        """Fit encoders on food dataset."""
        categories = [item.category for item in food_items]
        cuisines = [item.cuisine for item in food_items]
        
        self.category_encoder.fit(categories)
        self.cuisine_encoder.fit(cuisines)
        self._fitted = True
    
    def encode_user(self, user: User) -> UserFeatures:
        """Encode user features."""
        return UserFeatures(
            age=float(user.profile.age or 25),
            gender_encoded=self.gender_encoder.get(
                user.profile.gender.value if user.profile.gender else 'other', 2
            ),
            bmi=float(user.cached_bmi or 22),
            activity_encoded=self.activity_encoder.get(
                user.profile.activity_level.value, 2
            ),
            goal_encoded=self.goal_encoder.get(
                user.profile.goal.value, 1
            ),
            diet_type_encoded=self.diet_encoder.get(
                user.dietary_preferences.diet_type.value, 0
            ),
            daily_budget=float(user.budget_settings.daily_budget),
            target_calories=float(user.cached_target_calories or 2000)
        )
    
    def encode_food(self, item: FoodItem) -> FoodFeatures:
        """Encode food item features."""
        if not self._fitted:
            raise ValueError("Encoder not fitted. Call fit() first.")
        
        return FoodFeatures(
            calories=item.calories,
            protein=item.protein,
            carbs=item.carbs,
            fats=item.fats,
            price=item.price,
            is_veg=1 if item.is_veg else 0,
            category_encoded=int(self.category_encoder.transform([item.category])[0]),
            cuisine_encoded=int(self.cuisine_encoder.transform([item.cuisine])[0])
        )
    
    def create_feature_vector(self, user_features: UserFeatures, food_features: FoodFeatures) -> np.ndarray:
        """Create combined feature vector for prediction."""
        return np.array([
            user_features.age,
            user_features.gender_encoded,
            user_features.bmi,
            user_features.activity_encoded,
            user_features.goal_encoded,
            user_features.diet_type_encoded,
            user_features.daily_budget,
            user_features.target_calories,
            food_features.calories,
            food_features.protein,
            food_features.carbs,
            food_features.fats,
            food_features.price,
            food_features.is_veg,
            food_features.category_encoded,
            food_features.cuisine_encoded
        ])


class RecommendationEngine:
    """
    ML-based recommendation engine using Random Forest.
    
    Combines rule-based filtering with ML scoring for personalized recommendations.
    """
    
    def __init__(self):
        self.encoder = FeatureEncoder()
        self.model: Optional[RandomForestClassifier] = None
        self.feedback_history: List[UserFeedback] = []
        self._initialized = False
        self.model_path = Path("ml_models/recommender.pkl")
    
    def initialize(self):
        """Initialize the recommendation engine."""
        food_dataset.ensure_loaded()
        items = food_dataset.get_all_items()
        self.encoder.fit(items)
        self._initialized = True
    
    def _ensure_initialized(self):
        """Ensure engine is initialized."""
        if not self._initialized:
            self.initialize()
    
    def train_model(self, training_data: List[Tuple[User, FoodItem, int]]):
        """
        Train the recommendation model.
        
        Args:
            training_data: List of (user, food_item, rating) tuples
        """
        self._ensure_initialized()
        
        if len(training_data) < 10:
            print("Not enough training data. Using rule-based recommendations.")
            return
        
        X = []
        y = []
        
        for user, item, rating in training_data:
            user_features = self.encoder.encode_user(user)
            food_features = self.encoder.encode_food(item)
            feature_vector = self.encoder.create_feature_vector(user_features, food_features)
            
            X.append(feature_vector)
            # Convert rating to binary: 1 if rating >= 4, else 0
            y.append(1 if rating >= 4 else 0)
        
        X = np.array(X)
        y = np.array(y)
        
        # Train Random Forest
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.model.fit(X, y)
        
        print(f"Model trained on {len(X)} samples")
    
    def save_model(self):
        """Save trained model to disk."""
        if self.model:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'encoder': self.encoder
                }, f)
    
    def load_model(self) -> bool:
        """Load model from disk."""
        if self.model_path.exists():
            try:
                with open(self.model_path, 'rb') as f:
                    data = pickle.load(f)
                    self.model = data['model']
                    self.encoder = data['encoder']
                    self._initialized = True
                    return True
            except Exception as e:
                print(f"Error loading model: {e}")
        return False
    
    def _calculate_rule_based_score(
        self,
        item: FoodItem,
        user: User,
        meal_slot: Optional[str] = None
    ) -> float:
        """
        Calculate rule-based recommendation score.
        
        Considers: diet match, budget fit, nutritional alignment, allergen safety
        """
        score = 50.0  # Base score
        
        # Diet type match
        if user.dietary_preferences.diet_type.value == 'veg' and item.is_veg:
            score += 10
        elif user.dietary_preferences.diet_type.value == 'non_veg':
            score += 5
        
        # Budget efficiency
        if item.price <= user.budget_settings.daily_budget * 0.4:
            score += 10
        elif item.price <= user.budget_settings.daily_budget * 0.3:
            score += 15
        
        # Goal alignment
        goal = user.profile.goal
        if goal == Goal.WEIGHT_LOSS:
            # Prefer high protein, low calorie
            if item.protein >= 15:
                score += 10
            if item.calories < 300:
                score += 10
        elif goal == Goal.WEIGHT_GAIN:
            # Prefer high calorie
            if item.calories >= 400:
                score += 10
            if item.protein >= 20:
                score += 5
        
        # Allergen penalty
        user_allergens = [a.lower() for a in user.dietary_preferences.allergies]
        for allergen in item.allergens:
            if allergen.lower() in user_allergens:
                score -= 100  # Heavy penalty
        
        # Cuisine preference bonus
        if item.cuisine in user.dietary_preferences.preferred_cuisines:
            score += 15
        
        # Nutritional density bonus
        if item.nutritional_density > 0.5:
            score += 10
        
        return max(0, min(100, score))
    
    def _calculate_ml_score(
        self,
        item: FoodItem,
        user: User
    ) -> float:
        """Calculate ML-based recommendation score."""
        if not self.model:
            return 50.0  # Default if no model
        
        user_features = self.encoder.encode_user(user)
        food_features = self.encoder.encode_food(item)
        feature_vector = self.encoder.create_feature_vector(user_features, food_features)
        
        # Get probability of positive class
        proba = self.model.predict_proba(feature_vector.reshape(1, -1))[0]
        return proba[1] * 100 if len(proba) > 1 else 50.0
    
    def get_recommendations(
        self,
        user: User,
        meal_slot: Optional[str] = None,
        limit: int = 10,
        exclude_items: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get personalized food recommendations.
        
        Args:
            user: User to recommend for
            meal_slot: Optional meal slot for filtering
            limit: Maximum recommendations
            exclude_items: Items to exclude
            
        Returns:
            List of recommendations with scores
        """
        self._ensure_initialized()
        
        # Get all items
        items = food_dataset.get_all_items()
        
        # Filter by diet type
        diet = user.dietary_preferences.diet_type
        if diet == DietType.VEG:
            items = [i for i in items if i.is_veg]
        elif diet == DietType.VEGAN:
            items = [i for i in items if i.is_veg and 'dairy' not in i.allergens]
        
        # Exclude specified items
        if exclude_items:
            exclude_lower = [e.lower() for e in exclude_items]
            items = [i for i in items if i.name.lower() not in exclude_lower]
        
        # Filter out allergens
        allergies = [a.lower() for a in user.dietary_preferences.allergies]
        items = [i for i in items if not any(a in allergies for a in i.allergens)]
        
        # Calculate scores
        scored_items = []
        for item in items:
            rule_score = self._calculate_rule_based_score(item, user, meal_slot)
            
            if self.model:
                ml_score = self._calculate_ml_score(item, user)
                # Weighted combination: 40% rules, 60% ML
                final_score = 0.4 * rule_score + 0.6 * ml_score
            else:
                final_score = rule_score
            
            scored_items.append({
                'item': item,
                'score': final_score,
                'rule_score': rule_score
            })
        
        # Sort by score
        scored_items.sort(key=lambda x: x['score'], reverse=True)
        
        # Format response
        recommendations = []
        for entry in scored_items[:limit]:
            item = entry['item']
            recommendations.append({
                'name': item.name,
                'calories': item.calories,
                'protein': item.protein,
                'carbs': item.carbs,
                'fats': item.fats,
                'price': item.price,
                'is_veg': item.is_veg,
                'category': item.category,
                'cuisine': item.cuisine,
                'score': round(entry['score'], 1),
                'reason': self._generate_recommendation_reason(item, user)
            })
        
        return recommendations
    
    def _generate_recommendation_reason(self, item: FoodItem, user: User) -> str:
        """Generate human-readable reason for recommendation."""
        reasons = []
        
        if item.protein >= 15:
            reasons.append("High protein")
        
        if item.price <= user.budget_settings.daily_budget * 0.25:
            reasons.append("Budget friendly")
        
        if user.profile.goal == Goal.WEIGHT_LOSS and item.calories < 300:
            reasons.append("Low calorie")
        
        if item.cuisine in user.dietary_preferences.preferred_cuisines:
            reasons.append(f"{item.cuisine} cuisine")
        
        if item.nutritional_density > 0.5:
            reasons.append("Good value")
        
        return ", ".join(reasons[:3]) if reasons else "Matches your preferences"
    
    def record_feedback(
        self,
        user_id: str,
        food_item_name: str,
        rating: int,
        meal_slot: str,
        was_consumed: bool = True
    ):
        """Record user feedback for future model training."""
        feedback = UserFeedback(
            user_id=user_id,
            food_item_name=food_item_name,
            rating=rating,
            meal_slot=meal_slot,
            timestamp=datetime.utcnow(),
            was_consumed=was_consumed
        )
        self.feedback_history.append(feedback)
    
    def get_similar_items(self, item_name: str, limit: int = 5) -> List[Dict]:
        """Find items similar to a given item."""
        self._ensure_initialized()
        
        target = food_dataset.get_item(item_name)
        if not target:
            return []
        
        items = food_dataset.get_all_items()
        
        scored = []
        for item in items:
            if item.name == target.name:
                continue
            
            # Calculate similarity based on nutrition
            calorie_sim = 1 - abs(item.calories - target.calories) / max(target.calories, 1)
            protein_sim = 1 - abs(item.protein - target.protein) / max(target.protein, 1)
            price_sim = 1 - abs(item.price - target.price) / max(target.price, 1)
            veg_match = 1 if item.is_veg == target.is_veg else 0
            
            similarity = (calorie_sim + protein_sim + price_sim + veg_match) / 4
            
            scored.append({
                'item': item,
                'similarity': similarity * 100
            })
        
        scored.sort(key=lambda x: x['similarity'], reverse=True)
        
        return [
            {
                'name': s['item'].name,
                'calories': s['item'].calories,
                'protein': s['item'].protein,
                'price': s['item'].price,
                'is_veg': s['item'].is_veg,
                'similarity': round(s['similarity'], 1)
            }
            for s in scored[:limit]
        ]


# Singleton instance
recommendation_engine = RecommendationEngine()
