from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models.user import User
from app.services.user_service import user_service
from app.services.health_calculator import health_calculator

users_bp = Blueprint('users', __name__)


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
    """Helper to build user response dict from User model."""
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


@users_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user_profile():
    """Get current authenticated user's full profile."""
    try:
        identity = get_jwt_identity()
        
        if not identity:
            return jsonify({"detail": "Invalid token: no identity"}), 401
        
        # Handle both dict and string identity formats
        if isinstance(identity, dict):
            user_id = identity.get('user_id')
        else:
            user_id = identity
            
        if not user_id:
            return jsonify({"detail": "Invalid token: no user_id"}), 401
        
        current_user = user_service.get_user_by_id(user_id)
        
        if not current_user:
            return jsonify({"detail": "User not found"}), 404
        
        return jsonify(build_user_response(current_user))
    except Exception as e:
        return jsonify({"detail": f"Error: {str(e)}"}), 500


@users_bp.route('/me/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user's health profile."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"detail": "Invalid request data"}), 400
    
    from app.schemas.user import ProfileUpdate
    
    try:
        profile_data = ProfileUpdate(**data)
        updated_user = user_service.update_profile(current_user, profile_data)
        return jsonify(build_user_response(updated_user))
    except Exception as e:
        return jsonify({"detail": str(e)}), 400


@users_bp.route('/me/dietary-preferences', methods=['PUT'])
@jwt_required()
def update_dietary_preferences():
    """Update user's dietary preferences."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"detail": "Invalid request data"}), 400
    
    from app.schemas.user import DietaryPreferencesUpdate
    
    try:
        prefs_data = DietaryPreferencesUpdate(**data)
        updated_user = user_service.update_dietary_preferences(current_user, prefs_data)
        return jsonify(build_user_response(updated_user))
    except Exception as e:
        return jsonify({"detail": str(e)}), 400


@users_bp.route('/me/budget', methods=['PUT'])
@jwt_required()
def update_budget_settings():
    """Update user's budget settings."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"detail": "Invalid request data"}), 400
    
    from app.schemas.user import BudgetSettingsUpdate
    
    try:
        budget_data = BudgetSettingsUpdate(**data)
        updated_user = user_service.update_budget_settings(current_user, budget_data)
        return jsonify(build_user_response(updated_user))
    except Exception as e:
        return jsonify({"detail": str(e)}), 400


@users_bp.route('/me/meals', methods=['PUT'])
@jwt_required()
def update_meal_configuration():
    """Update user's meal configuration."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"detail": "Invalid request data"}), 400
    
    from app.schemas.user import MealConfigUpdate
    
    try:
        meal_data = MealConfigUpdate(**data)
        updated_user = user_service.update_meal_config(current_user, meal_data)
        return jsonify(build_user_response(updated_user))
    except Exception as e:
        return jsonify({"detail": str(e)}), 400


@users_bp.route('/me/health-metrics', methods=['GET'])
@jwt_required()
def get_health_metrics():
    """Get detailed health metrics for current user."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    metrics = user_service.get_user_health_metrics(current_user)
    return jsonify(metrics)


@users_bp.route('/me/macro-targets', methods=['GET'])
@jwt_required()
def get_macro_targets():
    """Get macronutrient targets based on calorie goals."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    if not current_user.cached_target_calories:
        return jsonify({"detail": "Complete your profile to get macro targets"}), 400
    
    macros = health_calculator.get_macro_targets(
        current_user.cached_target_calories,
        current_user.profile.goal
    )
    
    return jsonify({
        "target_calories": current_user.cached_target_calories,
        "goal": current_user.profile.goal.value,
        **macros
    })
