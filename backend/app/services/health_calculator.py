from typing import Optional, Tuple
from app.models.user import User, ActivityLevel, Goal


class HealthCalculator:
    """Service for calculating health metrics: BMI, BMR, TDEE, and target calories."""
    
    # Activity level multipliers for TDEE calculation
    ACTIVITY_MULTIPLIERS = {
        ActivityLevel.SEDENTARY: 1.2,
        ActivityLevel.LIGHT: 1.375,
        ActivityLevel.MODERATE: 1.55,
        ActivityLevel.ACTIVE: 1.725,
        ActivityLevel.VERY_ACTIVE: 1.9
    }
    
    # Caloric adjustments for goals
    GOAL_ADJUSTMENTS = {
        Goal.WEIGHT_LOSS: -500,      # 500 kcal deficit
        Goal.WEIGHT_GAIN: 500,       # 500 kcal surplus
        Goal.MAINTENANCE: 0
    }
    
    @staticmethod
    def calculate_bmi(weight: float, height: float) -> Tuple[float, str]:
        """
        Calculate BMI and return category.
        
        Args:
            weight: Weight in kg
            height: Height in cm
            
        Returns:
            Tuple of (BMI value, BMI category)
        """
        height_m = height / 100  # Convert cm to meters
        bmi = weight / (height_m ** 2)
        bmi = round(bmi, 2)
        
        # Determine category
        if bmi < 18.5:
            category = "Underweight"
        elif 18.5 <= bmi < 25:
            category = "Normal"
        elif 25 <= bmi < 30:
            category = "Overweight"
        else:
            category = "Obese"
            
        return bmi, category
    
    @staticmethod
    def calculate_bmr(weight: float, height: float, age: int, gender: str) -> float:
        """
        Calculate Basal Metabolic Rate using Mifflin-St Jeor Equation.
        
        Args:
            weight: Weight in kg
            height: Height in cm
            age: Age in years
            gender: 'male' or 'female'
            
        Returns:
            BMR in kcal/day
        """
        # Mifflin-St Jeor Equation
        if gender.lower() == "male":
            bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
        else:
            bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
            
        return round(bmr, 2)
    
    @classmethod
    def calculate_tdee(cls, bmr: float, activity_level: ActivityLevel) -> float:
        """
        Calculate Total Daily Energy Expenditure.
        
        Args:
            bmr: Basal Metabolic Rate
            activity_level: User's activity level
            
        Returns:
            TDEE in kcal/day
        """
        multiplier = cls.ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
        tdee = bmr * multiplier
        return round(tdee, 2)
    
    @classmethod
    def calculate_target_calories(cls, tdee: float, goal: Goal) -> float:
        """
        Calculate target daily calorie intake based on goal.
        
        Args:
            tdee: Total Daily Energy Expenditure
            goal: User's fitness goal
            
        Returns:
            Target calories in kcal/day
        """
        adjustment = cls.GOAL_ADJUSTMENTS.get(goal, 0)
        target = tdee + adjustment
        
        # Ensure minimum safe calories
        min_calories = 1200
        return round(max(target, min_calories), 2)
    
    @classmethod
    def calculate_all_metrics(cls, user: User) -> dict:
        """
        Calculate all health metrics for a user.
        
        Args:
            user: User document
            
        Returns:
            Dictionary with all calculated metrics
        """
        profile = user.profile
        
        # Check if we have required data
        if not all([profile.weight, profile.height, profile.age, profile.gender]):
            return {
                "bmi": None,
                "bmi_category": None,
                "bmr": None,
                "tdee": None,
                "target_calories": None,
                "message": "Complete profile required for health calculations"
            }
        
        # Calculate metrics
        bmi, bmi_category = cls.calculate_bmi(profile.weight, profile.height)
        bmr = cls.calculate_bmr(
            profile.weight, 
            profile.height, 
            profile.age, 
            profile.gender.value
        )
        tdee = cls.calculate_tdee(bmr, profile.activity_level)
        target_calories = cls.calculate_target_calories(tdee, profile.goal)
        
        return {
            "bmi": bmi,
            "bmi_category": bmi_category,
            "bmr": bmr,
            "tdee": tdee,
            "target_calories": target_calories
        }
    
    @classmethod
    def get_macro_targets(cls, target_calories: float, goal: Goal) -> dict:
        """
        Calculate macronutrient targets based on calories and goal.
        
        Returns targets for protein, carbs, and fats in grams.
        """
        if goal == Goal.WEIGHT_LOSS:
            # Higher protein for muscle preservation
            protein_pct = 0.30
            carbs_pct = 0.40
            fats_pct = 0.30
        elif goal == Goal.WEIGHT_GAIN:
            # Higher carbs for energy
            protein_pct = 0.25
            carbs_pct = 0.50
            fats_pct = 0.25
        else:
            # Balanced for maintenance
            protein_pct = 0.25
            carbs_pct = 0.50
            fats_pct = 0.25
        
        # Convert percentages to grams
        # Protein: 4 kcal/g, Carbs: 4 kcal/g, Fats: 9 kcal/g
        protein_g = round((target_calories * protein_pct) / 4, 1)
        carbs_g = round((target_calories * carbs_pct) / 4, 1)
        fats_g = round((target_calories * fats_pct) / 9, 1)
        
        return {
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fats_g": fats_g,
            "protein_pct": protein_pct * 100,
            "carbs_pct": carbs_pct * 100,
            "fats_pct": fats_pct * 100
        }


# Singleton instance
health_calculator = HealthCalculator()
