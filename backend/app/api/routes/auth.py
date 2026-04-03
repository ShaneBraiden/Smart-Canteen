from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models.user import User
from app.services.user_service import user_service

auth_bp = Blueprint('auth', __name__)


def get_current_user():
    """Get current user from JWT identity."""
    identity = get_jwt_identity()
    
    if not identity:
        return None
    
    # Handle both dict and string formats
    if isinstance(identity, dict):
        user_id = identity.get('user_id')
    else:
        user_id = str(identity)
    
    if not user_id:
        return None
        
    return user_service.get_user_by_id(user_id)


def build_user_response(user: User) -> dict:
    """Build user response dictionary."""
    health_metrics = user_service.get_user_health_metrics(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "profile": {
            "age": user.profile.age,
            "gender": user.profile.gender.value if user.profile.gender else None,
            "height": user.profile.height,
            "weight": user.profile.weight,
            "activity_level": user.profile.activity_level.value,
            "goal": user.profile.goal.value
        },
        "dietary_preferences": {
            "diet_type": user.dietary_preferences.diet_type.value,
            "allergies": user.dietary_preferences.allergies,
            "disliked_foods": user.dietary_preferences.disliked_foods,
            "preferred_cuisines": user.dietary_preferences.preferred_cuisines
        },
        "budget_settings": {
            "daily_budget": user.budget_settings.daily_budget,
            "weekly_budget": user.budget_settings.weekly_budget,
            "monthly_budget": user.budget_settings.monthly_budget,
            "strict_mode": user.budget_settings.strict_mode
        },
        "health_metrics": {
            "bmi": health_metrics.get("bmi"),
            "bmi_category": health_metrics.get("bmi_category"),
            "bmr": health_metrics.get("bmr"),
            "tdee": health_metrics.get("tdee"),
            "target_calories": health_metrics.get("target_calories")
        },
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat()
    }


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()
    
    if not data:
        return jsonify({"detail": "Invalid request data"}), 400
    
    from app.schemas.user import UserRegister
    
    try:
        user_data = UserRegister(**data)
        user = user_service.create_user(user_data)
        return jsonify(build_user_response(user)), 201
    except ValueError as e:
        return jsonify({"detail": str(e)}), 400
    except Exception as e:
        return jsonify({"detail": str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token."""
    # Support both form data and JSON
    if request.content_type and 'form' in request.content_type:
        email = request.form.get('username')  # OAuth2 uses 'username' field
        password = request.form.get('password')
    else:
        data = request.get_json() or {}
        email = data.get('email')
        password = data.get('password')
    
    if not email or not password:
        return jsonify({"detail": "Email and password required"}), 400
    
    user = user_service.authenticate_user(email, password)
    
    if not user:
        return jsonify({"detail": "Incorrect email or password"}), 401
    
    token_data = user_service.create_user_token(user)
    return jsonify(token_data)


@auth_bp.route('/login/json', methods=['POST'])
def login_json():
    """Authenticate user with JSON body."""
    data = request.get_json()
    
    if not data:
        return jsonify({"detail": "Invalid request data"}), 400
    
    email = data.get('email')
    password = data.get('password')
    
    user = user_service.authenticate_user(email, password)
    
    if not user:
        return jsonify({"detail": "Incorrect email or password"}), 401
    
    token_data = user_service.create_user_token(user)
    return jsonify(token_data)
