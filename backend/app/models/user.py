from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class ActivityLevel(str, Enum):
    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    ACTIVE = "active"
    VERY_ACTIVE = "very_active"


class Goal(str, Enum):
    WEIGHT_LOSS = "weight_loss"
    WEIGHT_GAIN = "weight_gain"
    MAINTENANCE = "maintenance"


class DietType(str, Enum):
    VEG = "veg"
    NON_VEG = "non_veg"
    VEGAN = "vegan"
    EGGETARIAN = "eggetarian"


class MealSlot(str, Enum):
    BREAKFAST = "breakfast"
    MORNING_SNACK = "morning_snack"
    LUNCH = "lunch"
    EVENING_SNACK = "evening_snack"
    DINNER = "dinner"


class UserProfile(BaseModel):
    """Embedded profile information for health calculations."""
    age: Optional[int] = Field(None, ge=10, le=100)
    gender: Optional[Gender] = None
    height: Optional[float] = Field(None, ge=100, le=250)
    weight: Optional[float] = Field(None, ge=30, le=300)
    activity_level: ActivityLevel = ActivityLevel.MODERATE
    goal: Goal = Goal.MAINTENANCE


class DietaryPreferences(BaseModel):
    """Embedded dietary preferences and restrictions."""
    diet_type: DietType = DietType.VEG
    allergies: List[str] = Field(default_factory=list)
    disliked_foods: List[str] = Field(default_factory=list)
    preferred_cuisines: List[str] = Field(default_factory=list)


class BudgetSettings(BaseModel):
    """Embedded budget configuration."""
    daily_budget: float = Field(150.0, ge=50, le=1000)
    weekly_budget: Optional[float] = Field(None, ge=350, le=7000)
    monthly_budget: Optional[float] = Field(None, ge=1500, le=30000)
    strict_mode: bool = False


class MealConfiguration(BaseModel):
    """User's meal slot configuration."""
    enabled_meals: List[MealSlot] = Field(
        default_factory=lambda: [MealSlot.BREAKFAST, MealSlot.LUNCH, MealSlot.DINNER]
    )
    meal_budget_split: dict = Field(
        default_factory=lambda: {
            "breakfast": 0.25,
            "lunch": 0.40,
            "dinner": 0.35
        }
    )


class User:
    """User model for MongoDB (Flask/PyMongo version)."""
    
    COLLECTION = "users"
    
    def __init__(
        self,
        email: str,
        username: str,
        hashed_password: str,
        _id: Optional[ObjectId] = None,
        profile: Optional[Dict] = None,
        dietary_preferences: Optional[Dict] = None,
        budget_settings: Optional[Dict] = None,
        meal_config: Optional[Dict] = None,
        is_active: bool = True,
        is_verified: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        cached_bmi: Optional[float] = None,
        cached_bmr: Optional[float] = None,
        cached_tdee: Optional[float] = None,
        cached_target_calories: Optional[float] = None,
    ):
        self._id = _id or ObjectId()
        self.email = email
        self.username = username
        self.hashed_password = hashed_password
        self.profile = UserProfile(**(profile or {}))
        self.dietary_preferences = DietaryPreferences(**(dietary_preferences or {}))
        self.budget_settings = BudgetSettings(**(budget_settings or {}))
        self.meal_config = MealConfiguration(**(meal_config or {}))
        self.is_active = is_active
        self.is_verified = is_verified
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.cached_bmi = cached_bmi
        self.cached_bmr = cached_bmr
        self.cached_tdee = cached_tdee
        self.cached_target_calories = cached_target_calories
    
    @property
    def id(self) -> str:
        return str(self._id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "_id": self._id,
            "email": self.email,
            "username": self.username,
            "hashed_password": self.hashed_password,
            "profile": self.profile.model_dump(),
            "dietary_preferences": self.dietary_preferences.model_dump(),
            "budget_settings": self.budget_settings.model_dump(),
            "meal_config": self.meal_config.model_dump(),
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "cached_bmi": self.cached_bmi,
            "cached_bmr": self.cached_bmr,
            "cached_tdee": self.cached_tdee,
            "cached_target_calories": self.cached_target_calories,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """Create User instance from MongoDB document."""
        return cls(
            _id=data.get("_id"),
            email=data["email"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            profile=data.get("profile"),
            dietary_preferences=data.get("dietary_preferences"),
            budget_settings=data.get("budget_settings"),
            meal_config=data.get("meal_config"),
            is_active=data.get("is_active", True),
            is_verified=data.get("is_verified", False),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            cached_bmi=data.get("cached_bmi"),
            cached_bmr=data.get("cached_bmr"),
            cached_tdee=data.get("cached_tdee"),
            cached_target_calories=data.get("cached_target_calories"),
        )
