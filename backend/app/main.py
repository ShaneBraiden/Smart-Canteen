from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta

from app.core.config import settings
from app.core.database import init_db, get_db
from app.services.food_dataset import food_dataset
from app.ml.recommender import recommendation_engine


def create_app():
    """Application factory for Flask app."""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = settings.SECRET_KEY
    app.config['JWT_SECRET_KEY'] = settings.SECRET_KEY
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    app.config['MONGO_URI'] = settings.MONGODB_URL
    
    # JWT configuration - allow complex identity objects
    app.config['JWT_TOKEN_LOCATION'] = ['headers']
    app.config['JWT_HEADER_NAME'] = 'Authorization'
    app.config['JWT_HEADER_TYPE'] = 'Bearer'
    
    # Initialize extensions
    CORS(app, origins=["http://localhost:3000", "http://localhost:5173"], supports_credentials=True)
    jwt = JWTManager(app)
    
    # Configure JWT to work with dict identity
    app.config['JWT_IDENTITY_CLAIM'] = 'sub'
    
    # JWT error handlers
    @jwt.unauthorized_loader
    def unauthorized_callback(error_string):
        return jsonify({"detail": f"Missing or invalid token: {error_string}"}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        return jsonify({"detail": f"Invalid token: {error_string}"}), 422
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"detail": "Token has expired"}), 401
    
    # Initialize database
    init_db(app)
    
    # Load food dataset
    food_dataset.load()
    
    # Initialize ML engine
    recommendation_engine.initialize()
    
    # Register blueprints
    from app.api.routes.auth import auth_bp
    from app.api.routes.users import users_bp
    from app.api.routes.menu import menu_bp
    from app.api.routes.meals import meals_bp
    from app.api.routes.recommendations import recommendations_bp
    
    app.register_blueprint(auth_bp, url_prefix=f'{settings.API_V1_PREFIX}/auth')
    app.register_blueprint(users_bp, url_prefix=f'{settings.API_V1_PREFIX}/users')
    app.register_blueprint(menu_bp, url_prefix=f'{settings.API_V1_PREFIX}/menu')
    app.register_blueprint(meals_bp, url_prefix=f'{settings.API_V1_PREFIX}/meals')
    app.register_blueprint(recommendations_bp, url_prefix=f'{settings.API_V1_PREFIX}/recommendations')
    
    # Root endpoints
    @app.route('/')
    def root():
        return jsonify({
            "message": "Welcome to Smart Canteen System API",
            "version": "1.0.0",
            "docs": "/api/v1",
            "status": "healthy"
        })
    
    @app.route('/health')
    def health_check():
        return jsonify({"status": "healthy", "service": settings.APP_NAME})
    
    return app


# Create app instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=settings.DEBUG, host='0.0.0.0', port=8000)
