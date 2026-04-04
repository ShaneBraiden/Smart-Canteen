from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from typing import Optional

from app.services.user_service import user_service
from app.services.ocr_service import ocr_engine
from app.services.menu_parser import menu_parser
from app.services.food_dataset import food_dataset
from app.services.food_validator import food_validator
from app.services.scanned_menu_service import scanned_menu_service

menu_bp = Blueprint('menu', __name__)


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


@menu_bp.route('/extract', methods=['POST'])
@jwt_required()
def extract_menu_from_image():
    """
    Upload a menu image and extract food items with prices.
    
    OCR extracts text → ML validates nutrition → Items saved to user's DB.
    Use GET /scanned to retrieve saved items.
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    if 'file' not in request.files:
        return jsonify({"detail": "No file uploaded"}), 400
    
    file = request.files['file']
    
    # Check if we should replace existing items or merge
    replace_items = request.form.get('replace', 'false').lower() == 'true'
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg']
    if file.content_type not in allowed_types:
        return jsonify({
            "detail": f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        }), 400
    
    contents = file.read()
    
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        return jsonify({"detail": "File too large. Maximum 10MB."}), 400
    
    try:
        # Run OCR
        ocr_result = ocr_engine.process_menu_image(contents)
        
        # Parse menu text
        extracted_items = menu_parser.parse_menu_text(ocr_result['text'])
        
        # Build items list for saving
        items_to_save = []
        for item in extracted_items:
            items_to_save.append({
                'name': item.name,
                'price': item.price
            })
        
        # Save to user's scanned menu in MongoDB
        user_id = str(current_user.id)
        saved_menu = scanned_menu_service.add_scanned_items(
            user_id=user_id,
            extracted_items=items_to_save,
            replace=replace_items
        )
        
        # Build response with validated items from DB
        validated_items = []
        for item in saved_menu.items:
            # Find matching extracted item for OCR confidence
            ocr_conf = 0.8  # default
            for ext_item in extracted_items:
                if ext_item.name.lower() == item.name.lower():
                    ocr_conf = ext_item.confidence
                    break
            
            validated_items.append({
                "name": item.name,
                "cleaned_name": item.cleaned_name,
                "price": item.price,
                "calories": item.calories,
                "protein": item.protein,
                "carbs": item.carbs,
                "fats": item.fats,
                "is_veg": item.is_veg,
                "category": item.category,
                "validation_source": item.validation_source,
                "confidence": item.confidence,
                "database_match": item.database_match,
                "ocr_confidence": ocr_conf
            })
        
        return jsonify({
            "success": True,
            "message": f"Scanned {len(extracted_items)} items, saved {len(saved_menu.items)} to your menu",
            "ocr_confidence": ocr_result['average_confidence'],
            "items_extracted": len(extracted_items),
            "items_saved": len(saved_menu.items),
            "validated_items": validated_items,
            "menu_stats": scanned_menu_service.get_menu_stats(user_id),
            "preprocessing_used": ocr_result.get('preprocessing_used', True),
            "model_status": food_validator.get_model_status()
        })
        
    except RuntimeError as e:
        return jsonify({"detail": f"OCR is unavailable: {str(e)}"}), 503
    except Exception as e:
        return jsonify({"detail": f"OCR processing failed: {str(e)}"}), 500


@menu_bp.route('/scanned', methods=['GET'])
@jwt_required()
def get_scanned_menu():
    """
    Get user's saved scanned menu items.
    
    These are the items validated by ML and saved to database.
    Use these items for meal plan generation.
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    user_id = str(current_user.id)
    menu = scanned_menu_service.get_user_menu(user_id)
    
    if not menu or not menu.items:
        return jsonify({
            "success": True,
            "items": [],
            "total_items": 0,
            "message": "No scanned menu items. Upload a menu image first."
        })
    
    return jsonify({
        "success": True,
        "items": [item.to_dict() for item in menu.items],
        "total_items": len(menu.items),
        "stats": scanned_menu_service.get_menu_stats(user_id),
        "last_scan": menu.last_scan_at.isoformat() if menu.last_scan_at else None
    })


@menu_bp.route('/scanned', methods=['DELETE'])
@jwt_required()
def clear_scanned_menu():
    """Clear all items from user's scanned menu."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    user_id = str(current_user.id)
    scanned_menu_service.clear_menu(user_id)
    
    return jsonify({
        "success": True,
        "message": "Scanned menu cleared"
    })


@menu_bp.route('/scanned/<item_name>', methods=['DELETE'])
@jwt_required()
def remove_scanned_item(item_name: str):
    """Remove a specific item from scanned menu."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    user_id = str(current_user.id)
    removed = scanned_menu_service.remove_item(user_id, item_name)
    
    if not removed:
        return jsonify({"detail": "Item not found in menu"}), 404
    
    return jsonify({
        "success": True,
        "message": f"Removed '{item_name}' from menu"
    })


@menu_bp.route('/scanned/stats', methods=['GET'])
@jwt_required()
def get_scanned_menu_stats():
    """Get statistics about user's scanned menu."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    user_id = str(current_user.id)
    stats = scanned_menu_service.get_menu_stats(user_id)
    
    return jsonify({
        "success": True,
        "stats": stats
    })


@menu_bp.route('/search', methods=['GET'])
@jwt_required()
def search_food_items():
    """Search for food items in the database."""
    query = request.args.get('query', '')
    limit = int(request.args.get('limit', 10))
    
    items = food_dataset.search(query, limit=limit)
    
    return jsonify([{
        "name": item.name,
        "calories": item.calories,
        "protein": item.protein,
        "carbs": item.carbs,
        "fats": item.fats,
        "is_veg": item.is_veg,
        "allergens": item.allergens,
        "price": item.price,
        "category": item.category,
        "cuisine": item.cuisine
    } for item in items])


@menu_bp.route('/items', methods=['GET'])
def list_food_items():
    """List food items with optional filters."""
    category = request.args.get('category')
    cuisine = request.args.get('cuisine')
    is_veg_str = request.args.get('is_veg')
    max_price = request.args.get('max_price')
    limit = int(request.args.get('limit', 50))
    
    items = food_dataset.get_all_items()
    
    # Apply filters
    if category:
        items = [i for i in items if i.category.lower() == category.lower()]
    if cuisine:
        items = [i for i in items if i.cuisine.lower() == cuisine.lower()]
    if is_veg_str is not None:
        is_veg = is_veg_str.lower() in ('true', '1', 'yes')
        items = [i for i in items if i.is_veg == is_veg]
    if max_price:
        items = [i for i in items if i.price <= float(max_price)]
    
    items = items[:limit]
    
    return jsonify([{
        "name": item.name,
        "calories": item.calories,
        "protein": item.protein,
        "carbs": item.carbs,
        "fats": item.fats,
        "is_veg": item.is_veg,
        "allergens": item.allergens,
        "price": item.price,
        "category": item.category,
        "cuisine": item.cuisine
    } for item in items])


@menu_bp.route('/stats', methods=['GET'])
def get_dataset_stats():
    """Get statistics about the food dataset."""
    return jsonify(food_dataset.get_stats())


@menu_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get list of food categories."""
    stats = food_dataset.get_stats()
    return jsonify({"categories": stats['categories']})


@menu_bp.route('/cuisines', methods=['GET'])
def get_cuisines():
    """Get list of cuisines."""
    stats = food_dataset.get_stats()
    return jsonify({"cuisines": stats['cuisines']})


@menu_bp.route('/validate', methods=['POST'])
@jwt_required()
def validate_food_items():
    """
    Validate food items using ML model and database matching.
    
    Request body:
        {
            "items": ["idli", "masala dosa", "unknown dish"]
        }
    
    Returns validated nutrition info with confidence scores.
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    data = request.get_json()
    if not data or 'items' not in data:
        return jsonify({"detail": "Missing 'items' in request body"}), 400
    
    items = data['items']
    if not isinstance(items, list):
        return jsonify({"detail": "'items' must be a list of food names"}), 400
    
    if len(items) > 50:
        return jsonify({"detail": "Maximum 50 items per request"}), 400
    
    # Validate each item
    results = food_validator.validate_batch(items)
    
    return jsonify({
        "success": True,
        "count": len(results),
        "validated_items": [r.to_dict() for r in results],
        "model_status": food_validator.get_model_status()
    })


@menu_bp.route('/validate/single', methods=['GET'])
@jwt_required()
def validate_single_food():
    """
    Validate a single food item by query parameter.
    
    Query params:
        food: The food name to validate
    
    Example: /api/menu/validate/single?food=masala+dosa
    """
    food_name = request.args.get('food', '')
    
    if not food_name:
        return jsonify({"detail": "Missing 'food' query parameter"}), 400
    
    result = food_validator.validate(food_name)
    
    return jsonify({
        "success": True,
        "validation": result.to_dict()
    })


@menu_bp.route('/model/status', methods=['GET'])
def get_model_status():
    """Get the status of the ML nutrition estimator model."""
    return jsonify(food_validator.get_model_status())


# ==================== Menu History Endpoints ====================

@menu_bp.route('/history', methods=['GET'])
@jwt_required()
def get_menu_history():
    """
    Get all saved menus for the user (history).
    
    Returns list of menus with summary info (not full item details).
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    user_id = str(current_user.id)
    menus = scanned_menu_service.get_user_menus(user_id)
    
    return jsonify({
        "success": True,
        "menus": [menu.to_summary() for menu in menus],
        "total": len(menus)
    })


@menu_bp.route('/save', methods=['POST'])
@jwt_required()
def save_menu_with_name():
    """
    Save scanned menu items with a user-given name.
    
    Request body:
        {
            "name": "College Canteen Menu",
            "items": [{"name": "Idli", "price": 20}, ...]
        }
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"detail": "Missing request body"}), 400
    
    menu_name = data.get('name', '').strip()
    if not menu_name:
        return jsonify({"detail": "Menu name is required"}), 400
    
    items = data.get('items', [])
    if not items:
        return jsonify({"detail": "No items to save"}), 400
    
    user_id = str(current_user.id)
    saved_menu = scanned_menu_service.save_menu_with_name(
        user_id=user_id,
        extracted_items=items,
        menu_name=menu_name
    )
    
    return jsonify({
        "success": True,
        "message": f"Menu '{menu_name}' saved with {len(saved_menu.items)} items",
        "menu": saved_menu.to_summary(),
        "menu_id": str(saved_menu.id)
    })


@menu_bp.route('/<menu_id>', methods=['GET'])
@jwt_required()
def get_menu_by_id(menu_id: str):
    """Get a specific menu by ID with full item details."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    user_id = str(current_user.id)
    menu = scanned_menu_service.get_menu_by_id(menu_id, user_id)
    
    if not menu:
        return jsonify({"detail": "Menu not found"}), 404
    
    return jsonify({
        "success": True,
        "menu": {
            "id": str(menu.id),
            "name": menu.name,
            "items": [item.to_dict() for item in menu.items],
            "total_items": len(menu.items),
            "created_at": menu.created_at.isoformat() if menu.created_at else None,
            "last_scan_at": menu.last_scan_at.isoformat() if menu.last_scan_at else None
        }
    })


@menu_bp.route('/<menu_id>', methods=['DELETE'])
@jwt_required()
def delete_menu(menu_id: str):
    """Delete a specific menu."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    user_id = str(current_user.id)
    deleted = scanned_menu_service.delete_menu(menu_id, user_id)
    
    if not deleted:
        return jsonify({"detail": "Menu not found"}), 404
    
    return jsonify({
        "success": True,
        "message": "Menu deleted"
    })


@menu_bp.route('/<menu_id>/rename', methods=['PATCH'])
@jwt_required()
def rename_menu(menu_id: str):
    """Rename a menu."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    data = request.get_json()
    new_name = data.get('name', '').strip() if data else ''
    
    if not new_name:
        return jsonify({"detail": "New name is required"}), 400
    
    user_id = str(current_user.id)
    renamed = scanned_menu_service.rename_menu(menu_id, user_id, new_name)
    
    if not renamed:
        return jsonify({"detail": "Menu not found"}), 404
    
    return jsonify({
        "success": True,
        "message": f"Menu renamed to '{new_name}'"
    })
