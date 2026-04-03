from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from enum import Enum

from app.models.user import MealSlot
from app.services.user_service import user_service
from app.services.optimizer import budget_optimizer
from app.services.food_dataset import food_dataset

meals_bp = Blueprint('meals', __name__)


class PlanDuration(str, Enum):
    THREE_DAYS = "3"
    SEVEN_DAYS = "7"
    THIRTY_DAYS = "30"


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


def format_plan_response(result) -> dict:
    """Format MealPlanResult into API response."""
    days = []
    
    for daily in result.days:
        meals = []
        for slot, items in daily.meals.items():
            meal_items = [
                {
                    "name": item.food_item.name,
                    "calories": item.total_calories,
                    "protein": item.total_protein,
                    "carbs": item.total_carbs,
                    "fats": item.total_fats,
                    "price": item.total_price,
                    "is_veg": item.food_item.is_veg
                } for item in items
            ]
            meals.append({
                "slot": slot.value,
                "items": meal_items,
                "total_calories": sum(i["calories"] for i in meal_items),
                "total_cost": sum(i["price"] for i in meal_items)
            })
        
        days.append({
            "day": daily.day,
            "meals": meals,
            "daily_calories": daily.total_calories,
            "daily_cost": daily.total_cost
        })
    
    return {
        "success": result.success,
        "message": result.message,
        "plan": days,
        "summary": {
            'total_days': len(result.days),
            'total_cost': round(result.total_cost, 2),
            'average_daily_calories': round(result.average_daily_calories, 1),
            'average_daily_cost': round(result.total_cost / len(result.days), 2) if result.days else 0,
            'budget_used_pct': 0
        }
    }


@meals_bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_meal_plan():
    """Generate an optimized meal plan based on user profile and budget."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    duration = request.args.get('duration', '7')
    if duration not in ['3', '7', '30']:
        duration = '7'
    
    if not current_user.cached_target_calories:
        return jsonify({
            "detail": "Please complete your profile first. Required: age, gender, height, weight"
        }), 400
    
    num_days = int(duration)
    result = budget_optimizer.generate_multi_day_plan(current_user, num_days)
    
    if not result.success:
        return jsonify({"detail": result.message}), 400
    
    response = format_plan_response(result)
    
    # Calculate budget usage
    daily_budget = current_user.budget_settings.daily_budget
    total_budget = daily_budget * num_days
    response['summary']['budget_used_pct'] = round((result.total_cost / total_budget) * 100, 1)
    
    return jsonify(response)


@meals_bp.route('/today', methods=['GET'])
@jwt_required()
def get_todays_plan():
    """Generate a meal plan for today only."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    if not current_user.cached_target_calories:
        return jsonify({"detail": "Please complete your profile first"}), 400
    
    daily_plan = budget_optimizer.generate_daily_plan(current_user, day_number=1)
    
    meals = []
    for slot, items in daily_plan.meals.items():
        meal_items = [
            {
                "name": item.food_item.name,
                "calories": item.total_calories,
                "protein": item.total_protein,
                "carbs": item.total_carbs,
                "fats": item.total_fats,
                "price": item.total_price,
                "is_veg": item.food_item.is_veg
            } for item in items
        ]
        meals.append({
            "slot": slot.value,
            "items": meal_items,
            "total_calories": sum(i["calories"] for i in meal_items),
            "total_cost": sum(i["price"] for i in meal_items)
        })
    
    return jsonify({
        "day": 1,
        "meals": meals,
        "daily_calories": daily_plan.total_calories,
        "daily_cost": daily_plan.total_cost
    })


@meals_bp.route('/substitute', methods=['POST'])
@jwt_required()
def find_item_substitutes():
    """Find budget-friendly substitutes for a food item."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"detail": "Invalid request data"}), 400
    
    item_name = data.get('item_name')
    max_price = data.get('max_price')
    
    if not item_name or not max_price:
        return jsonify({"detail": "item_name and max_price are required"}), 400
    
    # Find original item
    original = food_dataset.get_item(item_name)
    if not original:
        match = food_dataset.fuzzy_match(item_name)
        if not match.matched_item:
            return jsonify({"detail": "Food item not found"}), 404
        original = match.matched_item
    
    # Find substitutes
    substitutes = budget_optimizer.find_substitutes(
        original, 
        float(max_price), 
        current_user
    )
    
    max_savings = max(original.price - s.price for s in substitutes) if substitutes else 0
    
    return jsonify({
        "original": {
            "name": original.name,
            "calories": original.calories,
            "protein": original.protein,
            "carbs": original.carbs,
            "fats": original.fats,
            "price": original.price,
            "is_veg": original.is_veg
        },
        "substitutes": [
            {
                "name": s.name,
                "calories": s.calories,
                "protein": s.protein,
                "carbs": s.carbs,
                "fats": s.fats,
                "price": s.price,
                "is_veg": s.is_veg
            } for s in substitutes
        ],
        "max_savings": round(max_savings, 2)
    })


@meals_bp.route('/recommendations', methods=['GET'])
@jwt_required()
def get_quick_recommendations():
    """Get quick meal recommendations for a specific slot or general."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    meal_slot_str = request.args.get('meal_slot')
    max_price = float(request.args.get('max_price', 100))
    
    meal_slot = None
    if meal_slot_str:
        try:
            meal_slot = MealSlot(meal_slot_str)
        except ValueError:
            pass
    
    # Get filtered items
    all_items = budget_optimizer._filter_items_for_user(current_user)
    
    # Filter by price
    items = [i for i in all_items if i.price <= max_price]
    
    # Filter by meal slot category if specified
    if meal_slot:
        categories = budget_optimizer.MEAL_CATEGORIES.get(meal_slot, [])
        items = [i for i in items if i.category in categories] or items[:20]
    
    # Sort by nutritional density
    items.sort(key=lambda x: x.nutritional_density, reverse=True)
    
    return jsonify({
        'meal_slot': meal_slot.value if meal_slot else 'any',
        'max_price': max_price,
        'recommendations': [
            {
                'name': i.name,
                'calories': i.calories,
                'protein': i.protein,
                'price': i.price,
                'is_veg': i.is_veg,
                'category': i.category,
                'score': round(i.nutritional_density, 2)
            } for i in items[:10]
        ]
    })
