from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from app.models.user import (
    Gender, ActivityLevel, Goal, DietType, MealSlot
)


# ============== AUTH SCHEMAS ==============

class UserRegister(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "john_doe",
                "password": "securepassword123"
            }
        }


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenData(BaseModel):
    """Decoded token data."""
    user_id: Optional[str] = None
    email: Optional[str] = None


# ============== PROFILE SCHEMAS ==============

class ProfileUpdate(BaseModel):
    """Schema for updating user profile."""
    age: Optional[int] = Field(None, ge=10, le=100)
    gender: Optional[Gender] = None
    height: Optional[float] = Field(None, ge=100, le=250)
    weight: Optional[float] = Field(None, ge=30, le=300)
    activity_level: Optional[ActivityLevel] = None
    goal: Optional[Goal] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "age": 25,
                "gender": "male",
                "height": 175,
                "weight": 70,
                "activity_level": "moderate",
                "goal": "weight_loss"
            }
        }


class DietaryPreferencesUpdate(BaseModel):
    """Schema for updating dietary preferences."""
    diet_type: Optional[DietType] = None
    allergies: Optional[List[str]] = None
    disliked_foods: Optional[List[str]] = None
    preferred_cuisines: Optional[List[str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "diet_type": "veg",
                "allergies": ["nuts", "dairy"],
                "disliked_foods": ["bitter gourd"],
                "preferred_cuisines": ["South Indian"]
            }
        }


class BudgetSettingsUpdate(BaseModel):
    """Schema for updating budget settings."""
    daily_budget: Optional[float] = Field(None, ge=50, le=1000)
    weekly_budget: Optional[float] = Field(None, ge=350, le=7000)
    monthly_budget: Optional[float] = Field(None, ge=1500, le=30000)
    strict_mode: Optional[bool] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "daily_budget": 120,
                "strict_mode": True
            }
        }


class MealConfigUpdate(BaseModel):
    """Schema for updating meal configuration."""
    enabled_meals: Optional[List[MealSlot]] = None
    meal_budget_split: Optional[dict] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "enabled_meals": ["breakfast", "lunch", "evening_snack", "dinner"],
                "meal_budget_split": {
                    "breakfast": 0.20,
                    "lunch": 0.35,
                    "evening_snack": 0.10,
                    "dinner": 0.35
                }
            }
        }


# ============== RESPONSE SCHEMAS ==============

class ProfileResponse(BaseModel):
    """Profile data in response."""
    age: Optional[int]
    gender: Optional[str]
    height: Optional[float]
    weight: Optional[float]
    activity_level: str
    goal: str


class DietaryPreferencesResponse(BaseModel):
    """Dietary preferences in response."""
    diet_type: str
    allergies: List[str]
    disliked_foods: List[str]
    preferred_cuisines: List[str]


class BudgetSettingsResponse(BaseModel):
    """Budget settings in response."""
    daily_budget: float
    weekly_budget: Optional[float]
    monthly_budget: Optional[float]
    strict_mode: bool


class HealthMetricsResponse(BaseModel):
    """Calculated health metrics."""
    bmi: Optional[float]
    bmi_category: Optional[str]
    bmr: Optional[float]
    tdee: Optional[float]
    target_calories: Optional[float]


class UserResponse(BaseModel):
    """Full user response (without password)."""
    id: str
    email: str
    username: str
    profile: ProfileResponse
    dietary_preferences: DietaryPreferencesResponse
    budget_settings: BudgetSettingsResponse
    health_metrics: HealthMetricsResponse
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    success: bool = True
