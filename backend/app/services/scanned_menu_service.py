"""
Scanned Menu Service - Manages user's scanned menu items in MongoDB.

Workflow:
1. User uploads menu image → OCR extracts text
2. ML model validates/predicts nutrition for each item
3. Items are saved as a named menu in user's collection
4. Meal planner uses selected menu (not static database)
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

from app.core.database import get_collection
from app.models.scanned_menu import ScannedMenu, ScannedFoodItem
from app.services.food_validator import food_validator, ValidationResult


class ScannedMenuService:
    """Service for managing user's scanned menu items."""
    
    @staticmethod
    def get_collection():
        return get_collection(ScannedMenu.COLLECTION)
    
    # ==================== Menu History (Multiple Menus) ====================
    
    @staticmethod
    def get_user_menus(user_id: str) -> List[ScannedMenu]:
        """Get all menus for a user (history)."""
        docs = ScannedMenuService.get_collection().find(
            {"user_id": user_id}
        ).sort("updated_at", -1)  # Most recent first
        return [ScannedMenu.from_dict(doc) for doc in docs]
    
    @staticmethod
    def get_menu_by_id(menu_id: str, user_id: str) -> Optional[ScannedMenu]:
        """Get a specific menu by ID."""
        try:
            doc = ScannedMenuService.get_collection().find_one({
                "_id": ObjectId(menu_id),
                "user_id": user_id
            })
            return ScannedMenu.from_dict(doc) if doc else None
        except:
            return None
    
    @staticmethod
    def delete_menu(menu_id: str, user_id: str) -> bool:
        """Delete a specific menu."""
        try:
            result = ScannedMenuService.get_collection().delete_one({
                "_id": ObjectId(menu_id),
                "user_id": user_id
            })
            return result.deleted_count > 0
        except:
            return False
    
    @staticmethod
    def rename_menu(menu_id: str, user_id: str, new_name: str) -> bool:
        """Rename a menu."""
        try:
            result = ScannedMenuService.get_collection().update_one(
                {"_id": ObjectId(menu_id), "user_id": user_id},
                {"$set": {"name": new_name, "updated_at": datetime.utcnow().isoformat()}}
            )
            return result.modified_count > 0
        except:
            return False
    
    # ==================== Legacy single-menu methods (for backward compat) ====================
    
    @staticmethod
    def get_user_menu(user_id: str) -> Optional[ScannedMenu]:
        """Get user's most recent scanned menu."""
        doc = ScannedMenuService.get_collection().find_one(
            {"user_id": user_id},
            sort=[("updated_at", -1)]
        )
        return ScannedMenu.from_dict(doc) if doc else None
    
    @staticmethod
    def create_or_get_menu(user_id: str, name: str = "Untitled Menu") -> ScannedMenu:
        """Get existing menu or create new one."""
        menu = ScannedMenuService.get_user_menu(user_id)
        if menu:
            return menu
        
        # Create new menu
        menu = ScannedMenu(user_id=user_id, name=name, items=[])
        ScannedMenuService.get_collection().insert_one(menu.to_dict())
        return menu
    
    @staticmethod
    def _is_likely_food_item(name: str) -> bool:
        """
        Filter out non-food items like headers, URLs, restaurant names, etc.
        
        Returns True if the name is likely a food item.
        """
        name_lower = name.lower().strip()
        
        # Too short to be a food item
        if len(name_lower) < 3:
            return False
        
        # Skip URLs and web addresses
        if any(x in name_lower for x in ['www.', '.com', '.net', '.org', 'http', '://']):
            return False
        
        # Skip common menu headers and non-food words
        non_food_words = [
            'restaurant', 'menu', 'cafe', 'cafeteria', 'canteen', 'bistro',
            'kitchen', 'diner', 'eatery', 'grill', 'house', 'place',
            'welcome', 'order', 'special', 'today', 'daily', 'weekly',
            'breakfast', 'lunch', 'dinner', 'snacks', 'beverages', 'desserts',  # section headers
            'starters', 'appetizers', 'main course', 'sides', 'extras',
            'veg', 'non-veg', 'vegetarian', 'non vegetarian',
            'price', 'rate', 'cost', 'total', 'amount',
            'thank', 'thanks', 'visit', 'again', 'enjoy',
            'phone', 'call', 'address', 'contact', 'email',
            'open', 'close', 'hours', 'timing', 'delivery',
            'offer', 'discount', 'combo', 'deal',
            'copyright', 'rights', 'reserved', 'all rights',
        ]
        
        # Check if the entire name is a non-food word
        if name_lower in non_food_words:
            return False
        
        # Check if starts with numbers only (like table numbers)
        if name_lower.replace(' ', '').isdigit():
            return False
        
        # Check if it's mostly non-alphabetic
        alpha_chars = sum(c.isalpha() for c in name_lower)
        if alpha_chars < len(name_lower) * 0.5:
            return False
        
        # Check for common food keywords (positive indicators)
        food_keywords = [
            # Dishes
            'rice', 'biryani', 'pulao', 'curry', 'masala', 'dal', 'daal',
            'roti', 'naan', 'paratha', 'chapati', 'puri', 'bread',
            'dosa', 'idli', 'vada', 'upma', 'uttapam', 'sambar',
            'paneer', 'chicken', 'mutton', 'fish', 'prawn', 'egg',
            'steak', 'fillet', 'chop', 'roast', 'grilled', 'fried',
            'pasta', 'noodles', 'spaghetti', 'macaroni', 'lasagna',
            'pizza', 'burger', 'sandwich', 'wrap', 'roll',
            'soup', 'salad', 'fries', 'chips',
            'samosa', 'pakora', 'bhaji', 'bhel', 'chaat',
            # Beverages
            'tea', 'coffee', 'chai', 'juice', 'shake', 'smoothie',
            'lassi', 'buttermilk', 'coke', 'pepsi', 'soda', 'water',
            'milk', 'chocolate', 'mocktail', 'cocktail', 'lemonade',
            # Desserts
            'ice cream', 'kulfi', 'halwa', 'kheer', 'gulab jamun',
            'rasgulla', 'jalebi', 'sweet', 'cake', 'pastry', 'pudding',
            # General food terms
            'veg', 'vegetable', 'special', 'plain', 'butter', 'cheese',
            'cream', 'sauce', 'gravy', 'spicy', 'mild', 'hot',
            'combo', 'thali', 'platter', 'meal', 'portion',
            'beef', 'pork', 'lamb', 'ribeye', 'sirloin', 'tenderloin',
            'salmon', 'tuna', 'shrimp', 'lobster', 'crab',
            'orange', 'apple', 'mango', 'banana', 'fruit',
        ]
        
        # If it contains food keywords, it's likely food
        if any(kw in name_lower for kw in food_keywords):
            return True
        
        # If it's a single word and not in our food keywords, be stricter
        words = name_lower.split()
        if len(words) == 1:
            # Single words that are too generic
            generic_words = ['menu', 'restaurant', 'special', 'order', 'item']
            if name_lower in generic_words:
                return False
        
        # Default: assume it's food if it passed other filters
        # (Menu items that don't match our keywords might still be valid)
        return True
    
    @staticmethod
    def add_scanned_items(
        user_id: str,
        extracted_items: List[Dict[str, Any]],
        replace: bool = False
    ) -> ScannedMenu:
        """
        Add OCR-extracted items to user's menu after ML validation.
        
        Args:
            user_id: User ID
            extracted_items: List of dicts with 'name' and optional 'price'
            replace: If True, replace existing items. If False, append/update.
            
        Returns:
            Updated ScannedMenu
        """
        # Validate each item with ML model
        validated_items = []
        
        for item in extracted_items:
            name = item.get('name', '').strip()
            price = item.get('price')
            
            if not name:
                continue
            
            # Filter out non-food items
            if not ScannedMenuService._is_likely_food_item(name):
                continue
            
            # Validate with ML model
            validation: ValidationResult = food_validator.validate(name)
            
            # Determine is_veg
            is_veg = True
            if validation.db_match:
                is_veg = validation.db_match.is_veg
            else:
                non_veg_keywords = ['chicken', 'mutton', 'fish', 'prawn', 'egg', 'meat', 'keema', 'lamb', 'pork', 'beef', 'steak', 'bacon', 'ham', 'salmon', 'tuna', 'shrimp']
                is_veg = not any(kw in name.lower() for kw in non_veg_keywords)
            
            # Determine category
            category = 'Lunch'
            if validation.db_match:
                category = validation.db_match.category
            else:
                name_lower = name.lower()
                if any(kw in name_lower for kw in ['tea', 'coffee', 'juice', 'lassi', 'milk', 'shake', 'water', 'chocolate', 'cocktail']):
                    category = 'Beverages'
                elif any(kw in name_lower for kw in ['idli', 'dosa', 'upma', 'paratha', 'poha', 'omelette']):
                    category = 'Breakfast'
                elif any(kw in name_lower for kw in ['samosa', 'pakora', 'bhel', 'chaat', 'vada', 'fries']):
                    category = 'Snacks'
                elif any(kw in name_lower for kw in ['gulab', 'halwa', 'kheer', 'ice cream', 'sweet', 'jalebi', 'cake', 'pastry']):
                    category = 'Desserts'
            
            scanned_item = ScannedFoodItem(
                name=name,
                cleaned_name=validation.cleaned_name,
                extracted_price=float(price) if price else None,
                calories=validation.calories,
                protein=validation.protein,
                carbs=validation.carbs,
                fats=validation.fats,
                is_veg=is_veg,
                category=category,
                validation_source=validation.source,
                confidence=validation.confidence,
                database_match=validation.db_match.name if validation.db_match else None,
                added_at=datetime.utcnow()
            )
            
            validated_items.append(scanned_item)
        
        # Create new menu with given name (always creates new, for history)
        menu_name = f"Menu {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        
        menu_data = {
            'user_id': user_id,
            'name': menu_name,
            'items': [item.to_dict() for item in validated_items],
            'last_scan_at': datetime.utcnow().isoformat(),
            'total_items': len(validated_items),
            'ml_predictions_count': sum(1 for i in validated_items if i.validation_source == 'ml_prediction'),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = ScannedMenuService.get_collection().insert_one(menu_data)
        
        # Return the newly created menu
        return ScannedMenuService.get_menu_by_id(str(result.inserted_id), user_id)
    
    @staticmethod
    def save_menu_with_name(
        user_id: str,
        extracted_items: List[Dict[str, Any]],
        menu_name: str
    ) -> ScannedMenu:
        """
        Save OCR-extracted items as a new named menu.
        
        Args:
            user_id: User ID
            extracted_items: List of dicts with 'name' and optional 'price'
            menu_name: User-given name for this menu
            
        Returns:
            New ScannedMenu
        """
        # Validate each item with ML model
        validated_items = []
        
        for item in extracted_items:
            name = item.get('name', '').strip()
            price = item.get('price')
            
            if not name:
                continue
            
            # Filter out non-food items
            if not ScannedMenuService._is_likely_food_item(name):
                continue
            
            # Validate with ML model
            validation: ValidationResult = food_validator.validate(name)
            
            # Determine is_veg
            is_veg = True
            if validation.db_match:
                is_veg = validation.db_match.is_veg
            else:
                non_veg_keywords = ['chicken', 'mutton', 'fish', 'prawn', 'egg', 'meat', 'keema', 'lamb', 'pork', 'beef', 'steak', 'bacon', 'ham', 'salmon', 'tuna', 'shrimp']
                is_veg = not any(kw in name.lower() for kw in non_veg_keywords)
            
            # Determine category
            category = 'Lunch'
            if validation.db_match:
                category = validation.db_match.category
            else:
                name_lower = name.lower()
                if any(kw in name_lower for kw in ['tea', 'coffee', 'juice', 'lassi', 'milk', 'shake', 'water', 'chocolate', 'cocktail']):
                    category = 'Beverages'
                elif any(kw in name_lower for kw in ['idli', 'dosa', 'upma', 'paratha', 'poha', 'omelette']):
                    category = 'Breakfast'
                elif any(kw in name_lower for kw in ['samosa', 'pakora', 'bhel', 'chaat', 'vada', 'fries']):
                    category = 'Snacks'
                elif any(kw in name_lower for kw in ['gulab', 'halwa', 'kheer', 'ice cream', 'sweet', 'jalebi', 'cake', 'pastry']):
                    category = 'Desserts'
            
            scanned_item = ScannedFoodItem(
                name=name,
                cleaned_name=validation.cleaned_name,
                extracted_price=float(price) if price else None,
                calories=validation.calories,
                protein=validation.protein,
                carbs=validation.carbs,
                fats=validation.fats,
                is_veg=is_veg,
                category=category,
                validation_source=validation.source,
                confidence=validation.confidence,
                database_match=validation.db_match.name if validation.db_match else None,
                added_at=datetime.utcnow()
            )
            
            validated_items.append(scanned_item)
        
        # Create new menu with given name
        menu_data = {
            'user_id': user_id,
            'name': menu_name,
            'items': [item.to_dict() for item in validated_items],
            'last_scan_at': datetime.utcnow().isoformat(),
            'total_items': len(validated_items),
            'ml_predictions_count': sum(1 for i in validated_items if i.validation_source == 'ml_prediction'),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        result = ScannedMenuService.get_collection().insert_one(menu_data)
        
        # Return the newly created menu
        return ScannedMenuService.get_menu_by_id(str(result.inserted_id), user_id)
    
    @staticmethod
    def get_menu_items(user_id: str, menu_id: str = None) -> List[ScannedFoodItem]:
        """Get all items from a specific or most recent menu."""
        if menu_id:
            menu = ScannedMenuService.get_menu_by_id(menu_id, user_id)
        else:
            menu = ScannedMenuService.get_user_menu(user_id)
        return menu.items if menu else []
    
    @staticmethod
    def clear_menu(user_id: str) -> bool:
        """Clear all items from user's menu."""
        result = ScannedMenuService.get_collection().update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "items": [],
                    "updated_at": datetime.utcnow().isoformat(),
                    "total_items": 0,
                    "ml_predictions_count": 0
                }
            }
        )
        return result.modified_count > 0
    
    @staticmethod
    def remove_item(user_id: str, item_name: str) -> bool:
        """Remove a specific item from user's menu."""
        menu = ScannedMenuService.get_user_menu(user_id)
        if not menu:
            return False
        
        # Filter out the item
        new_items = [i for i in menu.items if i.name.lower() != item_name.lower()]
        
        if len(new_items) == len(menu.items):
            return False  # Item not found
        
        ScannedMenuService.get_collection().update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "items": [item.to_dict() for item in new_items],
                    "updated_at": datetime.utcnow().isoformat(),
                    "total_items": len(new_items)
                }
            }
        )
        return True
    
    @staticmethod
    def get_menu_stats(user_id: str) -> Dict[str, Any]:
        """Get statistics about user's scanned menu."""
        menu = ScannedMenuService.get_user_menu(user_id)
        
        if not menu or not menu.items:
            return {
                "total_items": 0,
                "veg_items": 0,
                "non_veg_items": 0,
                "categories": {},
                "avg_confidence": 0,
                "ml_predictions": 0,
                "database_matches": 0,
                "price_range": {"min": 0, "max": 0},
                "last_scan": None
            }
        
        items = menu.items
        veg_count = sum(1 for i in items if i.is_veg)
        
        # Category breakdown
        categories = {}
        for item in items:
            categories[item.category] = categories.get(item.category, 0) + 1
        
        # Confidence stats
        avg_confidence = sum(i.confidence for i in items) / len(items)
        
        # Source breakdown
        ml_predictions = sum(1 for i in items if i.validation_source == 'ml_prediction')
        db_matches = sum(1 for i in items if i.validation_source == 'database')
        
        # Price range
        prices = [i.price for i in items]
        
        return {
            "total_items": len(items),
            "veg_items": veg_count,
            "non_veg_items": len(items) - veg_count,
            "categories": categories,
            "avg_confidence": round(avg_confidence, 2),
            "ml_predictions": ml_predictions,
            "database_matches": db_matches,
            "hybrid_matches": len(items) - ml_predictions - db_matches,
            "price_range": {
                "min": round(min(prices), 2),
                "max": round(max(prices), 2)
            },
            "last_scan": menu.last_scan_at.isoformat() if menu.last_scan_at else None
        }


# Singleton instance
scanned_menu_service = ScannedMenuService()
