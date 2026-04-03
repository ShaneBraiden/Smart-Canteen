from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from typing import Optional

from app.models.user import MealSlot
from app.services.user_service import user_service
from app.ml.recommender import recommendation_engine

recommendations_bp = Blueprint('recommendations', __name__)


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


@recommendations_bp.route('/', methods=['GET'])
@jwt_required()
def get_recommendations():
    """Get personalized food recommendations based on ML model and rules."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    meal_slot_str = request.args.get('meal_slot')
    limit = int(request.args.get('limit', 10))
    exclude = request.args.get('exclude')
    
    if limit < 1:
        limit = 1
    elif limit > 50:
        limit = 50
    
    meal_slot = None
    if meal_slot_str:
        try:
            meal_slot = MealSlot(meal_slot_str)
        except ValueError:
            pass
    
    exclude_items = exclude.split(',') if exclude else None
    
    recommendations = recommendation_engine.get_recommendations(
        user=current_user,
        meal_slot=meal_slot.value if meal_slot else None,
        limit=limit,
        exclude_items=exclude_items
    )
    
    return jsonify(recommendations)


@recommendations_bp.route('/feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    """Submit feedback on a food item to improve recommendations."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"detail": "Invalid request data"}), 400
    
    food_item_name = data.get('food_item_name')
    rating = data.get('rating')
    meal_slot = data.get('meal_slot')
    was_consumed = data.get('was_consumed', True)
    
    if not food_item_name or rating is None or not meal_slot:
        return jsonify({"detail": "food_item_name, rating, and meal_slot are required"}), 400
    
    if not (1 <= rating <= 5):
        return jsonify({"detail": "Rating must be between 1 and 5"}), 400
    
    recommendation_engine.record_feedback(
        user_id=current_user.id,
        food_item_name=food_item_name,
        rating=rating,
        meal_slot=meal_slot,
        was_consumed=was_consumed
    )
    
    return jsonify({
        "success": True,
        "message": "Feedback recorded successfully"
    })


@recommendations_bp.route('/similar/<item_name>', methods=['GET'])
@jwt_required()
def get_similar_items(item_name: str):
    """Find items similar to a given food item."""
    limit = int(request.args.get('limit', 5))
    
    if limit < 1:
        limit = 1
    elif limit > 20:
        limit = 20
    
    similar = recommendation_engine.get_similar_items(item_name, limit=limit)
    
    if not similar:
        return jsonify({"detail": "Item not found"}), 404
    
    return jsonify(similar)


@recommendations_bp.route('/trending', methods=['GET'])
def get_trending_items():
    """Get trending food items based on recent feedback."""
    limit = int(request.args.get('limit', 10))
    
    if limit < 1:
        limit = 1
    elif limit > 20:
        limit = 20
    
    from app.services.food_dataset import food_dataset
    
    items = food_dataset.get_all_items()
    
    # Sort by nutritional density as proxy for popularity
    items.sort(key=lambda x: x.nutritional_density, reverse=True)
    
    return jsonify({
        "trending": [
            {
                "name": item.name,
                "calories": item.calories,
                "price": item.price,
                "category": item.category
            }
            for item in items[:limit]
        ]
    })


@recommendations_bp.route('/personalized-insights', methods=['GET'])
@jwt_required()
def get_personalized_insights():
    """Get personalized nutrition insights and tips."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    goal = current_user.profile.goal.value if current_user.profile.goal else "maintenance"
    target_calories = current_user.cached_target_calories or 2000
    budget = current_user.budget_settings.daily_budget
    
    insights = []
    
    if goal == "weight_loss":
        insights.append({
            "type": "tip",
            "title": "Weight Loss Focus",
            "message": f"Aim for {int(target_calories)} calories daily. Prioritize protein-rich foods."
        })
    elif goal == "weight_gain":
        insights.append({
            "type": "tip",
            "title": "Weight Gain Focus",
            "message": f"Target {int(target_calories)} calories daily. Include calorie-dense nutritious foods."
        })
    
    if budget < 100:
        insights.append({
            "type": "budget",
            "title": "Budget-Friendly Options",
            "message": "Try dal, rice, and seasonal vegetables for maximum nutrition per rupee."
        })
    
    insights.append({
        "type": "general",
        "title": "Stay Hydrated",
        "message": "Drink plenty of water. Buttermilk and coconut water are good hydrating options."
    })
    
    return jsonify({
        "user_goal": goal,
        "daily_target": target_calories,
        "daily_budget": budget,
        "insights": insights
    })
