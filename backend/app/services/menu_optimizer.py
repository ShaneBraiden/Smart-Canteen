"""
Menu-based Meal Plan Optimizer.

Generates meal plans from OCR-scanned menu items using ML-predicted nutrition.
Does NOT use the static database - only uses items from uploaded menus.
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import pulp

from app.models.user import User, MealSlot, Goal
from app.services.food_dataset import FoodItem
from app.services.food_validator import food_validator, ValidationResult


@dataclass
class ScannedMenuItem:
    """A menu item scanned via OCR with validated/predicted nutrition."""
    name: str
    extracted_price: Optional[float]
    validation: ValidationResult
    # Pre-validated fields (from MongoDB)
    _is_veg: Optional[bool] = None
    _category: Optional[str] = None
    
    @property
    def calories(self) -> float:
        return self.validation.calories
    
    @property
    def protein(self) -> float:
        return self.validation.protein
    
    @property
    def carbs(self) -> float:
        return self.validation.carbs
    
    @property
    def fats(self) -> float:
        return self.validation.fats
    
    @property
    def price(self) -> float:
        # Use extracted price if available, otherwise estimate
        if self.extracted_price and self.extracted_price > 0:
            return self.extracted_price
        # Estimate price based on calories (rough approximation)
        return max(20, min(150, self.calories * 0.15))
    
    @property
    def is_veg(self) -> bool:
        # Use pre-validated value if available
        if self._is_veg is not None:
            return self._is_veg
        # Check from database match or infer from name
        if self.validation.db_match:
            return self.validation.db_match.is_veg
        # Infer from name keywords
        non_veg_keywords = ['chicken', 'mutton', 'fish', 'prawn', 'egg', 'meat', 'keema']
        name_lower = self.name.lower()
        return not any(kw in name_lower for kw in non_veg_keywords)
    
    @property
    def category(self) -> str:
        # Use pre-validated value if available
        if self._category:
            return self._category
        # Get from database match or infer
        if self.validation.db_match:
            return self.validation.db_match.category
        # Infer from name
        name_lower = self.name.lower()
        if any(kw in name_lower for kw in ['tea', 'coffee', 'juice', 'lassi', 'milk']):
            return 'Beverages'
        if any(kw in name_lower for kw in ['idli', 'dosa', 'upma', 'paratha', 'poha']):
            return 'Breakfast'
        if any(kw in name_lower for kw in ['samosa', 'pakora', 'bhel', 'chaat']):
            return 'Snacks'
        if any(kw in name_lower for kw in ['gulab', 'halwa', 'kheer', 'ice cream']):
            return 'Desserts'
        return 'Lunch'  # Default
    
    @property
    def confidence(self) -> float:
        return self.validation.confidence
    
    def to_food_item(self) -> FoodItem:
        """Convert to FoodItem for compatibility with optimizer."""
        return FoodItem(
            name=self.name,
            calories=self.calories,
            protein=self.protein,
            carbs=self.carbs,
            fats=self.fats,
            is_veg=self.is_veg,
            allergens=self.validation.db_match.allergens if self.validation.db_match else [],
            price=self.price,
            category=self.category,
            cuisine=self.validation.db_match.cuisine if self.validation.db_match else 'Unknown'
        )
    
    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'extracted_price': self.extracted_price,
            'estimated_price': self.price,
            'calories': round(self.calories, 1),
            'protein': round(self.protein, 1),
            'carbs': round(self.carbs, 1),
            'fats': round(self.fats, 1),
            'is_veg': self.is_veg,
            'category': self.category,
            'confidence': round(self.confidence, 2),
            'source': self.validation.source
        }


@dataclass
class MenuMealPlanItem:
    """A single item in the menu-based meal plan."""
    menu_item: ScannedMenuItem
    meal_slot: MealSlot
    quantity: float = 1.0
    
    @property
    def total_calories(self) -> float:
        return self.menu_item.calories * self.quantity
    
    @property
    def total_protein(self) -> float:
        return self.menu_item.protein * self.quantity
    
    @property
    def total_carbs(self) -> float:
        return self.menu_item.carbs * self.quantity
    
    @property
    def total_fats(self) -> float:
        return self.menu_item.fats * self.quantity
    
    @property
    def total_price(self) -> float:
        return self.menu_item.price * self.quantity
    
    def to_dict(self) -> dict:
        return {
            'name': self.menu_item.name,
            'calories': round(self.total_calories, 1),
            'protein': round(self.total_protein, 1),
            'carbs': round(self.total_carbs, 1),
            'fats': round(self.total_fats, 1),
            'price': round(self.total_price, 2),
            'is_veg': self.menu_item.is_veg,
            'category': self.menu_item.category,
            'confidence': self.menu_item.confidence,
            'nutrition_source': self.menu_item.validation.source,
            'quantity': self.quantity
        }


@dataclass
class MenuDailyPlan:
    """A complete day's meal plan from scanned menu."""
    day: int
    meals: Dict[MealSlot, List[MenuMealPlanItem]] = field(default_factory=dict)
    
    @property
    def total_calories(self) -> float:
        return sum(item.total_calories for items in self.meals.values() for item in items)
    
    @property
    def total_protein(self) -> float:
        return sum(item.total_protein for items in self.meals.values() for item in items)
    
    @property
    def total_carbs(self) -> float:
        return sum(item.total_carbs for items in self.meals.values() for item in items)
    
    @property
    def total_fats(self) -> float:
        return sum(item.total_fats for items in self.meals.values() for item in items)
    
    @property
    def total_cost(self) -> float:
        return sum(item.total_price for items in self.meals.values() for item in items)
    
    def to_dict(self) -> dict:
        return {
            'day': self.day,
            'meals': {
                slot.value: [item.to_dict() for item in items]
                for slot, items in self.meals.items()
            },
            'totals': {
                'calories': round(self.total_calories, 1),
                'protein': round(self.total_protein, 1),
                'carbs': round(self.total_carbs, 1),
                'fats': round(self.total_fats, 1),
                'cost': round(self.total_cost, 2)
            }
        }


@dataclass
class MenuMealPlanResult:
    """Complete meal plan result from scanned menu."""
    success: bool
    days: List[MenuDailyPlan]
    total_cost: float
    average_daily_calories: float
    message: str
    menu_items_used: int
    ml_predictions_used: int
    
    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'days': [day.to_dict() for day in self.days],
            'summary': {
                'total_days': len(self.days),
                'total_cost': round(self.total_cost, 2),
                'average_daily_calories': round(self.average_daily_calories, 1),
                'average_daily_cost': round(self.total_cost / len(self.days), 2) if self.days else 0,
                'menu_items_used': self.menu_items_used,
                'ml_predictions_used': self.ml_predictions_used
            },
            'message': self.message
        }


class MenuMealPlanOptimizer:
    """
    Meal plan optimizer that uses ONLY scanned menu items.
    
    Uses ML model for nutrition prediction when items aren't in database.
    Uses PuLP for linear programming optimization.
    """
    
    # Meal slot calorie distribution
    MEAL_CALORIE_SPLIT = {
        MealSlot.BREAKFAST: 0.25,
        MealSlot.MORNING_SNACK: 0.10,
        MealSlot.LUNCH: 0.35,
        MealSlot.EVENING_SNACK: 0.10,
        MealSlot.DINNER: 0.20
    }
    
    # Category preferences for meal slots
    MEAL_CATEGORIES = {
        MealSlot.BREAKFAST: ['Breakfast', 'Healthy', 'Beverages'],
        MealSlot.MORNING_SNACK: ['Snacks', 'Fruits', 'Beverages'],
        MealSlot.LUNCH: ['Lunch', 'Healthy'],
        MealSlot.EVENING_SNACK: ['Snacks', 'Beverages'],
        MealSlot.DINNER: ['Lunch', 'Healthy', 'Dinner']
    }
    
    def __init__(self):
        self.validator = food_validator
    
    def validate_menu_items(
        self, 
        items: List[Dict[str, any]]
    ) -> List[ScannedMenuItem]:
        """
        Validate and enrich a list of OCR-extracted menu items.
        
        Args:
            items: List of dicts with 'name' and optional 'price' keys
                   Can also include 'pre_validated' dict with nutrition data
                   (for items already saved in MongoDB)
            
        Returns:
            List of ScannedMenuItem with ML-predicted nutrition
        """
        validated = []
        
        for item in items:
            name = item.get('name', '').strip()
            price = item.get('price')
            pre_validated = item.get('pre_validated')
            
            if not name:
                continue
            
            # If we have pre-validated nutrition (from MongoDB), use it
            is_veg = None
            category = None
            
            if pre_validated:
                # Create a ValidationResult from the pre-validated data
                from app.services.food_validator import ValidationResult
                validation = ValidationResult(
                    original_text=name,
                    cleaned_name=pre_validated.get('cleaned_name', name),
                    confidence=pre_validated.get('confidence', 0.9),
                    source=pre_validated.get('source', 'database'),
                    calories=pre_validated.get('calories', 0),
                    protein=pre_validated.get('protein', 0),
                    carbs=pre_validated.get('carbs', 0),
                    fats=pre_validated.get('fats', 0),
                    db_match=None,
                    ml_predicted=pre_validated.get('source') == 'ml_prediction'
                )
                # Get pre-validated is_veg and category
                is_veg = pre_validated.get('is_veg')
                category = pre_validated.get('category')
            else:
                # Validate with ML model
                validation = self.validator.validate(name)
            
            validated.append(ScannedMenuItem(
                name=name,
                extracted_price=float(price) if price else None,
                validation=validation,
                _is_veg=is_veg,
                _category=category
            ))
        
        return validated
    
    def _filter_items_for_user(
        self,
        items: List[ScannedMenuItem],
        user: User
    ) -> List[ScannedMenuItem]:
        """Filter menu items based on user preferences."""
        filtered = items.copy()
        
        # Filter by diet type
        diet_type = user.dietary_preferences.diet_type
        if diet_type.value in ['veg', 'vegan']:
            filtered = [i for i in filtered if i.is_veg]
        
        # Filter by disliked foods
        disliked = [d.lower() for d in user.dietary_preferences.disliked_foods]
        if disliked:
            filtered = [i for i in filtered 
                       if not any(d in i.name.lower() for d in disliked)]
        
        return filtered
    
    def _get_items_for_meal(
        self,
        items: List[ScannedMenuItem],
        meal_slot: MealSlot
    ) -> List[ScannedMenuItem]:
        """Get items appropriate for a meal slot."""
        preferred_categories = self.MEAL_CATEGORIES.get(meal_slot, [])
        
        # Prioritize items from preferred categories
        meal_items = [i for i in items if i.category in preferred_categories]
        
        # If not enough items, include others
        if len(meal_items) < 5:
            other_items = [i for i in items if i not in meal_items]
            meal_items.extend(other_items)
        
        return meal_items
    
    def _calculate_nutritional_score(
        self,
        item: ScannedMenuItem,
        goal: Goal
    ) -> float:
        """Calculate a nutritional score based on user goal."""
        # Add confidence bonus - prefer items we're sure about
        confidence_bonus = item.confidence * 10
        
        base_score = item.protein * 2 + confidence_bonus
        
        if goal == Goal.WEIGHT_LOSS:
            # Prefer high protein, low calorie
            if item.calories > 0:
                score = (item.protein * 3) / (item.calories / 100)
            else:
                score = base_score
        elif goal == Goal.WEIGHT_GAIN:
            # Prefer high calorie, high protein
            score = item.calories * 0.5 + item.protein * 2
        else:
            # Balanced
            score = base_score + item.carbs * 0.1
        
        return score + confidence_bonus
    
    def optimize_single_meal(
        self,
        available_items: List[ScannedMenuItem],
        target_calories: float,
        budget: float,
        goal: Goal,
        max_items: int = 3
    ) -> Tuple[List[ScannedMenuItem], float]:
        """
        Optimize a single meal using Linear Programming.
        
        Returns:
            Tuple of (selected items, total cost)
        """
        if not available_items:
            return [], 0
        
        # Create optimization problem
        prob = pulp.LpProblem("MenuMealOptimization", pulp.LpMaximize)
        
        # Decision variables: binary selection for each item
        item_vars = {}
        for i, item in enumerate(available_items):
            item_vars[i] = pulp.LpVariable(f"item_{i}", cat='Binary')
        
        # Objective: Maximize nutritional score
        scores = [self._calculate_nutritional_score(item, goal) for item in available_items]
        prob += pulp.lpSum([scores[i] * item_vars[i] for i in range(len(available_items))])
        
        # Constraint 1: Budget
        prob += pulp.lpSum([available_items[i].price * item_vars[i] 
                          for i in range(len(available_items))]) <= budget
        
        # Constraint 2: Calories (within 30% of target - more flexible for limited menus)
        prob += pulp.lpSum([available_items[i].calories * item_vars[i] 
                          for i in range(len(available_items))]) >= target_calories * 0.7
        prob += pulp.lpSum([available_items[i].calories * item_vars[i] 
                          for i in range(len(available_items))]) <= target_calories * 1.3
        
        # Constraint 3: Maximum items per meal
        prob += pulp.lpSum([item_vars[i] for i in range(len(available_items))]) <= max_items
        
        # Constraint 4: At least one item
        prob += pulp.lpSum([item_vars[i] for i in range(len(available_items))]) >= 1
        
        # Solve
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        
        # Extract selected items
        selected = []
        total_cost = 0
        
        if prob.status == pulp.LpStatusOptimal:
            for i, item in enumerate(available_items):
                if pulp.value(item_vars[i]) == 1:
                    selected.append(item)
                    total_cost += item.price
        else:
            # Fallback: select cheapest item that fits
            affordable = [i for i in available_items if i.price <= budget]
            if affordable:
                affordable.sort(key=lambda x: x.calories, reverse=True)
                selected = [affordable[0]]
                total_cost = affordable[0].price
        
        return selected, total_cost
    
    def generate_plan_from_menu(
        self,
        menu_items: List[Dict[str, any]],
        user: User,
        num_days: int = 1
    ) -> MenuMealPlanResult:
        """
        Generate meal plan from OCR-scanned menu items.
        
        Args:
            menu_items: List of dicts with 'name' and optional 'price'
            user: User with profile and preferences
            num_days: Number of days to plan
            
        Returns:
            MenuMealPlanResult with optimized meal plan
        """
        # Validate target calories
        if not user.cached_target_calories:
            return MenuMealPlanResult(
                success=False,
                days=[],
                total_cost=0,
                average_daily_calories=0,
                message="Please complete your profile to generate meal plans",
                menu_items_used=0,
                ml_predictions_used=0
            )
        
        # Validate and enrich menu items with ML
        validated_items = self.validate_menu_items(menu_items)
        
        if not validated_items:
            return MenuMealPlanResult(
                success=False,
                days=[],
                total_cost=0,
                average_daily_calories=0,
                message="No valid menu items found. Please upload a clear menu image.",
                menu_items_used=0,
                ml_predictions_used=0
            )
        
        # Filter for user preferences
        filtered_items = self._filter_items_for_user(validated_items, user)
        
        if not filtered_items:
            return MenuMealPlanResult(
                success=False,
                days=[],
                total_cost=0,
                average_daily_calories=0,
                message="No menu items match your dietary preferences.",
                menu_items_used=0,
                ml_predictions_used=0
            )
        
        # Count ML predictions
        ml_predictions = sum(1 for i in filtered_items if i.validation.ml_predicted)
        
        # Get user constraints
        daily_budget = user.budget_settings.daily_budget
        target_calories = user.cached_target_calories
        enabled_meals = user.meal_config.enabled_meals
        budget_split = user.meal_config.meal_budget_split
        goal = user.profile.goal
        
        days = []
        total_cost = 0
        total_calories = 0
        items_used = set()
        
        for day_num in range(1, num_days + 1):
            daily_plan = MenuDailyPlan(day=day_num)
            
            for meal_slot in enabled_meals:
                # Calculate meal budget and calories
                slot_key = meal_slot.value
                budget_ratio = budget_split.get(slot_key, 0.33)
                calorie_ratio = self.MEAL_CALORIE_SPLIT.get(meal_slot, 0.33)
                
                meal_budget = daily_budget * budget_ratio
                meal_calories = target_calories * calorie_ratio
                
                # Get items for this meal (exclude recently used for variety)
                available = [i for i in filtered_items if i.name not in items_used]
                if not available:
                    available = filtered_items  # Reset if all used
                
                meal_items = self._get_items_for_meal(available, meal_slot)
                
                # Optimize
                selected, cost = self.optimize_single_meal(
                    meal_items,
                    meal_calories,
                    meal_budget,
                    goal
                )
                
                # Add to plan
                daily_plan.meals[meal_slot] = [
                    MenuMealPlanItem(menu_item=item, meal_slot=meal_slot)
                    for item in selected
                ]
                
                # Track used items
                for item in selected:
                    items_used.add(item.name)
            
            days.append(daily_plan)
            total_cost += daily_plan.total_cost
            total_calories += daily_plan.total_calories
        
        avg_calories = total_calories / num_days if num_days > 0 else 0
        
        return MenuMealPlanResult(
            success=True,
            days=days,
            total_cost=total_cost,
            average_daily_calories=avg_calories,
            message=f"Generated {num_days}-day meal plan from {len(filtered_items)} menu items",
            menu_items_used=len(items_used),
            ml_predictions_used=ml_predictions
        )


# Singleton instance
menu_meal_optimizer = MenuMealPlanOptimizer()
