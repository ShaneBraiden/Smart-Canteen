from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from typing import Optional

from app.services.user_service import user_service
from app.services.ocr_service import ocr_engine
from app.services.menu_parser import menu_parser
from app.services.food_dataset import food_dataset

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
    """Upload a menu image and extract food items with prices."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({"detail": "User not found"}), 404
    
    if 'file' not in request.files:
        return jsonify({"detail": "No file uploaded"}), 400
    
    file = request.files['file']
    
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
        
        # Map to nutrition database
        mapped_items = []
        for item in extracted_items:
            match = food_dataset.fuzzy_match(item.name)
            
            mapped_items.append({
                "extracted_name": item.name,
                "extracted_price": item.price,
                "matched_name": match.matched_item.name if match.matched_item else None,
                "match_confidence": match.confidence,
                "nutrition": match.matched_item.to_dict() if match.matched_item else None,
                "alternatives": [name for name, _ in match.alternatives]
            })
        
        return jsonify({
            "success": True,
            "ocr_confidence": ocr_result['average_confidence'],
            "items_found": len(extracted_items),
            "extracted_items": [
                {
                    "name": item.name,
                    "price": item.price,
                    "confidence": item.confidence,
                    "raw_text": item.raw_text
                } for item in extracted_items
            ],
            "mapped_items": mapped_items,
            "preprocessing_used": ocr_result.get('preprocessing_used', True)
        })
        
    except RuntimeError as e:
        return jsonify({"detail": f"OCR is unavailable: {str(e)}"}), 503
    except Exception as e:
        return jsonify({"detail": f"OCR processing failed: {str(e)}"}), 500


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
