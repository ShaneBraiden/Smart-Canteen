from typing import Optional
from datetime import datetime
from bson import ObjectId

from app.core.database import get_collection
from app.models.user import User
from app.schemas.user import UserRegister, ProfileUpdate, DietaryPreferencesUpdate, BudgetSettingsUpdate, MealConfigUpdate
from app.core.security import get_password_hash, verify_password, create_token
from app.core.config import settings
from app.services.health_calculator import health_calculator


class UserService:
    """Service for user-related operations."""
    
    @staticmethod
    def get_collection():
        return get_collection(User.COLLECTION)
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Find user by email."""
        doc = UserService.get_collection().find_one({"email": email})
        return User.from_dict(doc) if doc else None
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[User]:
        """Find user by ID."""
        try:
            doc = UserService.get_collection().find_one({"_id": ObjectId(user_id)})
            return User.from_dict(doc) if doc else None
        except:
            return None
    
    @staticmethod
    def create_user(user_data: UserRegister) -> User:
        """Register a new user."""
        # Check if email already exists
        existing_user = UserService.get_user_by_email(user_data.email)
        if existing_user:
            raise ValueError("Email already registered")
        
        # Create user with hashed password
        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=get_password_hash(user_data.password)
        )
        
        UserService.get_collection().insert_one(user.to_dict())
        return user
    
    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = UserService.get_user_by_email(email)
        
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
            
        return user
    
    @staticmethod
    def create_user_token(user: User) -> dict:
        """Generate JWT token for user."""
        access_token = create_token(user.id, user.email)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    @staticmethod
    def update_profile(user: User, profile_data: ProfileUpdate) -> User:
        """Update user profile and recalculate health metrics."""
        update_data = profile_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(user.profile, field, value)
        
        # Recalculate health metrics
        metrics = health_calculator.calculate_all_metrics(user)
        user.cached_bmi = metrics.get("bmi")
        user.cached_bmr = metrics.get("bmr")
        user.cached_tdee = metrics.get("tdee")
        user.cached_target_calories = metrics.get("target_calories")
        user.updated_at = datetime.utcnow()
        
        UserService.get_collection().update_one(
            {"_id": user._id},
            {"$set": user.to_dict()}
        )
        return user
    
    @staticmethod
    def update_dietary_preferences(user: User, prefs_data: DietaryPreferencesUpdate) -> User:
        """Update user dietary preferences."""
        update_data = prefs_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(user.dietary_preferences, field, value)
        
        user.updated_at = datetime.utcnow()
        UserService.get_collection().update_one(
            {"_id": user._id},
            {"$set": user.to_dict()}
        )
        return user
    
    @staticmethod
    def update_budget_settings(user: User, budget_data: BudgetSettingsUpdate) -> User:
        """Update user budget settings."""
        update_data = budget_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(user.budget_settings, field, value)
        
        user.updated_at = datetime.utcnow()
        UserService.get_collection().update_one(
            {"_id": user._id},
            {"$set": user.to_dict()}
        )
        return user
    
    @staticmethod
    def update_meal_config(user: User, meal_data: MealConfigUpdate) -> User:
        """Update meal configuration."""
        update_data = meal_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(user.meal_config, field, value)
        
        user.updated_at = datetime.utcnow()
        UserService.get_collection().update_one(
            {"_id": user._id},
            {"$set": user.to_dict()}
        )
        return user
    
    @staticmethod
    def get_user_health_metrics(user: User) -> dict:
        """Get user's health metrics (cached or recalculated)."""
        if user.cached_bmi is not None:
            _, bmi_category = health_calculator.calculate_bmi(
                user.profile.weight, 
                user.profile.height
            ) if user.profile.weight and user.profile.height else (None, None)
            
            return {
                "bmi": user.cached_bmi,
                "bmi_category": bmi_category,
                "bmr": user.cached_bmr,
                "tdee": user.cached_tdee,
                "target_calories": user.cached_target_calories
            }
        
        return health_calculator.calculate_all_metrics(user)


# Singleton instance
user_service = UserService()
