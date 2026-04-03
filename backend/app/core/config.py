from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Smart Canteen System"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "smart_canteen"
    
    # JWT Authentication
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Food Dataset
    FOOD_DATASET_PATH: str = "data set/indian_food_composition.csv"

    # PaddleOCR Settings
    OCR_USE_GPU: bool = False  # Set to True if GPU available
    OCR_LANG: str = "en"  # Default language (en, hi, ta, te, etc.)
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
