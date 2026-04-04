from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from enum import Enum

from app.models.user import MealSlot
from app.services.user_service import user_service
from app.services.optimizer import budget_optimizer
from app.services.food_dataset import food_dataset
from app.services.menu_optimizer import menu_meal_optimizer
from app.services.scanned_menu_service import scanned_menu_service

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


@meals_bp.route('/generate-from-menu', methods=['POST'])
@jwt_required()
def generate_meal_plan_from_menu():
    """
    Generate an optimized meal plan from uploaded menu items.
    
    Uses ML model for nutrition prediction - does NOT use the static database.
    Only items from the uploaded menu are considered.
    
    Request body:
        {
            "menu_items": [
                {"name": "Masala Dosa", "price": 45},
                {"name": "Idli (2 pcs)", "price": 25},
                {"name": "Chicken Biryani", "price": 120}
            ],
            "days": 1  // Optional, default 1
        }
    
    Returns optimized meal plan with ML-predicted nutrition.
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    if not current_user.cached_target_calories:
        return jsonify({
            "detail": "Please complete your profile first. Required: age, gender, height, weight"
        }), 400
    
    data = request.get_json()
    if not data:
        return jsonify({"detail": "Invalid request data"}), 400
    
    menu_items = data.get('menu_items', [])
    num_days = int(data.get('days', 1))
    
    if not menu_items:
        return jsonify({"detail": "No menu_items provided"}), 400
    
    if not isinstance(menu_items, list):
        return jsonify({"detail": "menu_items must be a list"}), 400
    
    if num_days < 1 or num_days > 7:
        return jsonify({"detail": "days must be between 1 and 7"}), 400
    
    # Generate plan from menu items using ML
    result = menu_meal_optimizer.generate_plan_from_menu(
        menu_items=menu_items,
        user=current_user,
        num_days=num_days
    )
    
    if not result.success:
        return jsonify({"detail": result.message}), 400
    
    response = result.to_dict()
    
    # Add budget usage
    daily_budget = current_user.budget_settings.daily_budget
    total_budget = daily_budget * num_days
    response['summary']['budget_used_pct'] = round((result.total_cost / total_budget) * 100, 1)
    response['summary']['target_calories'] = current_user.cached_target_calories
    
    return jsonify(response)


@meals_bp.route('/validate-menu', methods=['POST'])
@jwt_required()
def validate_menu_for_planning():
    """
    Validate menu items before generating a meal plan.
    
    Returns nutrition info and confidence for each item.
    
    Request body:
        {
            "menu_items": [
                {"name": "Masala Dosa", "price": 45},
                {"name": "Unknown Dish"}
            ]
        }
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    data = request.get_json()
    if not data or 'menu_items' not in data:
        return jsonify({"detail": "menu_items required"}), 400
    
    menu_items = data.get('menu_items', [])
    
    # Validate each item
    validated = menu_meal_optimizer.validate_menu_items(menu_items)
    
    # Categorize by confidence
    high_conf = [i for i in validated if i.confidence >= 0.85]
    medium_conf = [i for i in validated if 0.7 <= i.confidence < 0.85]
    low_conf = [i for i in validated if i.confidence < 0.7]
    
    return jsonify({
        "total_items": len(validated),
        "high_confidence": len(high_conf),
        "medium_confidence": len(medium_conf),
        "low_confidence": len(low_conf),
        "items": [item.to_dict() for item in validated],
        "ready_for_planning": len(validated) >= 3,
        "message": f"Validated {len(validated)} items. {len(high_conf)} have high confidence nutrition data."
    })


@meals_bp.route('/generate-from-scanned', methods=['POST'])
@jwt_required()
def generate_meal_plan_from_scanned_menu():
    """
    Generate an optimized meal plan from user's SAVED scanned menu.
    
    Workflow:
    1. User scans menu image → OCR extracts text → ML validates → saved to DB
    2. This endpoint reads from that saved DB and generates meal plan
    
    Only items from the user's scanned menu (MongoDB) are used.
    
    Request body (optional):
        {
            "days": 1  // Optional, default 1 (max 7)
        }
    
    Returns optimized meal plan using ONLY items from user's scanned menu.
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    if not current_user.cached_target_calories:
        return jsonify({
            "detail": "Please complete your profile first. Required: age, gender, height, weight"
        }), 400
    
    user_id = str(current_user.id)
    
    # Get menu_id from request body (optional - uses most recent if not provided)
    data = request.get_json() or {}
    menu_id = data.get('menu_id')
    
    # Get user's saved scanned menu from MongoDB
    menu_items_db = scanned_menu_service.get_menu_items(user_id, menu_id)
    
    if not menu_items_db:
        return jsonify({
            "detail": "No scanned menu items found. Please scan a menu first using POST /api/v1/menu/extract",
            "hint": "Upload a menu image to scan food items before generating a meal plan"
        }), 400
    
    num_days = int(data.get('days', 1))
    
    if num_days < 1 or num_days > 7:
        return jsonify({"detail": "days must be between 1 and 7"}), 400
    
    # Convert saved DB items to the format expected by menu_optimizer
    menu_items = []
    for item in menu_items_db:
        menu_items.append({
            'name': item.name,
            'price': item.price,
            # Include pre-validated nutrition so ML doesn't re-predict
            'pre_validated': {
                'calories': item.calories,
                'protein': item.protein,
                'carbs': item.carbs,
                'fats': item.fats,
                'is_veg': item.is_veg,
                'category': item.category,
                'confidence': item.confidence,
                'source': item.validation_source
            }
        })
    
    # Generate plan from saved menu items
    result = menu_meal_optimizer.generate_plan_from_menu(
        menu_items=menu_items,
        user=current_user,
        num_days=num_days
    )
    
    if not result.success:
        return jsonify({"detail": result.message}), 400
    
    response = result.to_dict()
    
    # Add budget usage and menu stats
    daily_budget = current_user.budget_settings.daily_budget
    total_budget = daily_budget * num_days
    response['summary']['budget_used_pct'] = round((result.total_cost / total_budget) * 100, 1)
    response['summary']['target_calories'] = current_user.cached_target_calories
    response['summary']['menu_items_available'] = len(menu_items_db)
    response['summary']['menu_stats'] = scanned_menu_service.get_menu_stats(user_id)
    
    return jsonify(response)
