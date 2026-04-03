from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import pulp

from app.services.food_dataset import FoodItem, food_dataset
from app.models.user import User, MealSlot, DietType, Goal


@dataclass
class MealPlanItem:
    """A single item in the meal plan."""
    food_item: FoodItem
    meal_slot: MealSlot
    quantity: float = 1.0
    
    @property
    def total_calories(self) -> float:
        return self.food_item.calories * self.quantity
    
    @property
    def total_protein(self) -> float:
        return self.food_item.protein * self.quantity
    
    @property
    def total_carbs(self) -> float:
        return self.food_item.carbs * self.quantity
    
    @property
    def total_fats(self) -> float:
        return self.food_item.fats * self.quantity
    
    @property
    def total_price(self) -> float:
        return self.food_item.price * self.quantity
    
    def to_dict(self) -> dict:
        return {
            'food_item': self.food_item.to_dict(),
            'meal_slot': self.meal_slot.value,
            'quantity': self.quantity,
            'total_calories': self.total_calories,
            'total_protein': self.total_protein,
            'total_carbs': self.total_carbs,
            'total_fats': self.total_fats,
            'total_price': self.total_price
        }


@dataclass
class DailyMealPlan:
    """A complete day's meal plan."""
    day: int
    meals: Dict[MealSlot, List[MealPlanItem]] = field(default_factory=dict)
    
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
class MealPlanResult:
    """Complete meal plan result."""
    success: bool
    days: List[DailyMealPlan]
    total_cost: float
    average_daily_calories: float
    message: str
    
    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'days': [day.to_dict() for day in self.days],
            'summary': {
                'total_days': len(self.days),
                'total_cost': round(self.total_cost, 2),
                'average_daily_calories': round(self.average_daily_calories, 1),
                'average_daily_cost': round(self.total_cost / len(self.days), 2) if self.days else 0
            },
            'message': self.message
        }


class BudgetOptimizer:
    """
    Budget optimization engine using Linear Programming.
    
    Objective: Maximize nutritional value while staying within budget.
    Uses PuLP for solving the optimization problem.
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
        MealSlot.DINNER: ['Lunch', 'Healthy']  # Dinner uses lunch items
    }
    
    def __init__(self):
        self.dataset = food_dataset
    
    def _filter_items_for_user(self, user: User) -> List[FoodItem]:
        """Filter food items based on user preferences."""
        self.dataset.ensure_loaded()
        items = self.dataset.get_all_items()
        
        # Filter by diet type
        diet_type = user.dietary_preferences.diet_type
        if diet_type == DietType.VEG:
            items = [i for i in items if i.is_veg]
        elif diet_type == DietType.VEGAN:
            items = [i for i in items if i.is_veg and 'dairy' not in i.allergens]
        elif diet_type == DietType.EGGETARIAN:
            items = [i for i in items if i.is_veg or 'eggs' in ' '.join(i.allergens).lower()]
        
        # Filter out allergens
        allergies = [a.lower() for a in user.dietary_preferences.allergies]
        if allergies:
            items = [i for i in items 
                    if not any(allergen in allergies for allergen in i.allergens)]
        
        # Filter out disliked foods
        disliked = [d.lower() for d in user.dietary_preferences.disliked_foods]
        if disliked:
            items = [i for i in items 
                    if not any(d in i.name.lower() for d in disliked)]
        
        return items
    
    def _get_items_for_meal(self, items: List[FoodItem], meal_slot: MealSlot) -> List[FoodItem]:
        """Get items appropriate for a meal slot."""
        preferred_categories = self.MEAL_CATEGORIES.get(meal_slot, [])
        
        # Prioritize items from preferred categories
        meal_items = [i for i in items if i.category in preferred_categories]
        
        # If not enough items, include others
        if len(meal_items) < 10:
            other_items = [i for i in items if i not in meal_items]
            meal_items.extend(other_items[:20])
        
        return meal_items
    
    def _calculate_nutritional_score(self, item: FoodItem, goal: Goal) -> float:
        """Calculate a nutritional score for an item based on user goal."""
        base_score = item.protein * 2  # Protein is valuable
        
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
        
        return score
    
    def optimize_single_meal(
        self,
        available_items: List[FoodItem],
        target_calories: float,
        budget: float,
        goal: Goal,
        max_items: int = 3
    ) -> Tuple[List[FoodItem], float]:
        """
        Optimize a single meal using Linear Programming.
        
        Returns:
            Tuple of (selected items, total cost)
        """
        if not available_items:
            return [], 0
        
        # Create optimization problem
        prob = pulp.LpProblem("MealOptimization", pulp.LpMaximize)
        
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
        
        # Constraint 2: Calories (within 20% of target)
        prob += pulp.lpSum([available_items[i].calories * item_vars[i] 
                          for i in range(len(available_items))]) >= target_calories * 0.8
        prob += pulp.lpSum([available_items[i].calories * item_vars[i] 
                          for i in range(len(available_items))]) <= target_calories * 1.2
        
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
        
        return selected, total_cost
    
    def generate_daily_plan(
        self,
        user: User,
        day_number: int = 1,
        excluded_items: Optional[List[str]] = None
    ) -> DailyMealPlan:
        """
        Generate optimized meal plan for a single day.
        
        Args:
            user: User with profile and preferences
            day_number: Day number in the plan
            excluded_items: Items to exclude (for variety)
        """
        # Get user constraints
        daily_budget = user.budget_settings.daily_budget
        target_calories = user.cached_target_calories or 2000
        enabled_meals = user.meal_config.enabled_meals
        budget_split = user.meal_config.meal_budget_split
        goal = user.profile.goal
        
        # Get filtered items
        all_items = self._filter_items_for_user(user)
        
        # Exclude previously used items for variety
        if excluded_items:
            excluded_lower = [e.lower() for e in excluded_items]
            all_items = [i for i in all_items if i.name.lower() not in excluded_lower]
        
        daily_plan = DailyMealPlan(day=day_number)
        
        for meal_slot in enabled_meals:
            # Calculate meal budget and calories
            slot_key = meal_slot.value
            budget_ratio = budget_split.get(slot_key, 0.33)
            calorie_ratio = self.MEAL_CALORIE_SPLIT.get(meal_slot, 0.33)
            
            meal_budget = daily_budget * budget_ratio
            meal_calories = target_calories * calorie_ratio
            
            # Get items for this meal
            meal_items = self._get_items_for_meal(all_items, meal_slot)
            
            # Optimize
            selected, cost = self.optimize_single_meal(
                meal_items,
                meal_calories,
                meal_budget,
                goal
            )
            
            # Add to plan
            daily_plan.meals[meal_slot] = [
                MealPlanItem(food_item=item, meal_slot=meal_slot)
                for item in selected
            ]
        
        return daily_plan
    
    def generate_multi_day_plan(
        self,
        user: User,
        num_days: int = 7
    ) -> MealPlanResult:
        """
        Generate meal plan for multiple days with variety.
        
        Args:
            user: User with profile and preferences
            num_days: Number of days to plan (3, 7, or 30)
        """
        if not user.cached_target_calories:
            return MealPlanResult(
                success=False,
                days=[],
                total_cost=0,
                average_daily_calories=0,
                message="Please complete your profile to generate meal plans"
            )
        
        days = []
        used_items = []
        total_cost = 0
        total_calories = 0
        
        for day_num in range(1, num_days + 1):
            # Rotate exclusions to maintain variety
            recent_items = used_items[-30:] if len(used_items) > 30 else used_items
            
            daily_plan = self.generate_daily_plan(user, day_num, recent_items)
            days.append(daily_plan)
            
            # Track used items
            for items in daily_plan.meals.values():
                for item in items:
                    used_items.append(item.food_item.name)
            
            total_cost += daily_plan.total_cost
            total_calories += daily_plan.total_calories
        
        avg_calories = total_calories / num_days if num_days > 0 else 0
        
        return MealPlanResult(
            success=True,
            days=days,
            total_cost=total_cost,
            average_daily_calories=avg_calories,
            message=f"Generated {num_days}-day meal plan within budget"
        )
    
    def find_substitutes(
        self,
        item: FoodItem,
        max_price: float,
        user: User
    ) -> List[FoodItem]:
        """
        Find budget-friendly substitutes for an item.
        
        Args:
            item: Item to substitute
            max_price: Maximum price for substitute
            user: User for filtering
        """
        all_items = self._filter_items_for_user(user)
        
        substitutes = []
        for candidate in all_items:
            if candidate.name == item.name:
                continue
            if candidate.price > max_price:
                continue
            if candidate.is_veg != item.is_veg:
                continue
            
            # Check macro similarity (within 30%)
            protein_ok = abs(candidate.protein - item.protein) <= item.protein * 0.3 + 2
            calorie_ok = abs(candidate.calories - item.calories) <= item.calories * 0.3 + 50
            
            if protein_ok and calorie_ok:
                savings = item.price - candidate.price
                substitutes.append((candidate, savings))
        
        # Sort by savings
        substitutes.sort(key=lambda x: x[1], reverse=True)
        
        return [s[0] for s in substitutes[:5]]


# Singleton instance
budget_optimizer = BudgetOptimizer()
