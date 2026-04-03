from flask_pymongo import PyMongo
from pymongo import MongoClient
from app.core.config import settings

# MongoDB client instance
mongo = PyMongo()
client = None
db = None


def init_db(app):
    """Initialize database connection with Flask app."""
    global client, db
    mongo.init_app(app)
    client = MongoClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    print(f"Connected to MongoDB: {settings.DATABASE_NAME}")


def get_db():
    """Get database instance."""
    global db
    return db


def get_collection(name: str):
    """Get a specific collection."""
    return get_db()[name]
