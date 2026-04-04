"""
Training script for the Nutrition Estimator model.
Uses TF-IDF + Ridge regression to predict nutritional values from food names.

This model is used to validate and estimate nutrition for OCR-scanned food items
that may not exactly match database entries.
"""
import os
import sys
import re
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score, KFold
from sklearn.compose import TransformedTargetRegressor


# Target columns for prediction
TARGET_COLS = ['Calories', 'Protein', 'Carbs', 'Fats']


def clean_food_name(name: str) -> str:
    """Clean and normalize food name for consistent processing."""
    if pd.isna(name):
        return ''
    name = str(name).lower().strip()
    # Remove parenthetical info like "(2 pcs)" but keep meaningful parts
    name = re.sub(r'\s*\(\d+\s*pcs?\)', '', name)
    name = re.sub(r'\s*\(\d+g\)', '', name)
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


def load_indian_food_composition(data_dir: Path) -> pd.DataFrame:
    """Load and process indian_food_composition.csv (143 rows)."""
    path = data_dir / 'indian_food_composition.csv'
    df = pd.read_csv(path)
    
    # Standardize column names
    df = df.rename(columns={
        'Food_Item': 'Food_Name',
        'Calories': 'Calories',
        'Protein': 'Protein',
        'Carbs': 'Carbs',
        'Fats': 'Fats'
    })
    
    # Clean food names
    df['Food_Name'] = df['Food_Name'].apply(clean_food_name)
    
    # Keep only needed columns
    df = df[['Food_Name', 'Calories', 'Protein', 'Carbs', 'Fats']].copy()
    df['source'] = 'indian_food_composition'
    
    return df


def load_indian_food_nutrition_processed(data_dir: Path) -> pd.DataFrame:
    """Load and process Indian_Food_Nutrition_Processed.csv (1014 rows)."""
    path = data_dir / 'Indian_Food_Nutrition_Processed.csv'
    df = pd.read_csv(path)
    
    # Standardize column names
    df = df.rename(columns={
        'Dish Name': 'Food_Name',
        'Calories (kcal)': 'Calories',
        'Protein (g)': 'Protein',
        'Carbohydrates (g)': 'Carbs',
        'Fats (g)': 'Fats'
    })
    
    # Clean food names
    df['Food_Name'] = df['Food_Name'].apply(clean_food_name)
    
    # Keep only needed columns
    df = df[['Food_Name', 'Calories', 'Protein', 'Carbs', 'Fats']].copy()
    df['source'] = 'indian_food_nutrition_processed'
    
    return df


def parse_nutrient_value(value):
    """Parse nutrient value, handling formats like '72g', '6.2g', etc."""
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float)):
        return float(value)
    # Remove 'g', 'mg', etc. and convert
    value = str(value).lower().replace('g', '').replace('mg', '').strip()
    try:
        return float(value)
    except ValueError:
        return np.nan


def load_nutrition_fallback(data_dir: Path) -> pd.DataFrame:
    """Load nutrition.csv as fallback (8789 rows) - sample only unique items."""
    path = data_dir / 'nutrition.csv'
    df = pd.read_csv(path)
    
    # This dataset has columns: name, calories, protein, carbohydrate, total_fat
    df = df.rename(columns={
        'name': 'Food_Name',
        'calories': 'Calories',
        'protein': 'Protein',
        'carbohydrate': 'Carbs',
        'total_fat': 'Fats'
    })
    
    df['Food_Name'] = df['Food_Name'].apply(clean_food_name)
    
    # Parse nutrient values (they may have 'g' suffix)
    for col in ['Calories', 'Protein', 'Carbs', 'Fats']:
        df[col] = df[col].apply(parse_nutrient_value)
    
    df = df[['Food_Name', 'Calories', 'Protein', 'Carbs', 'Fats']].copy()
    df['source'] = 'nutrition_fallback'
    
    # Sample 500 diverse items to avoid overwhelming the primary datasets
    if len(df) > 500:
        df = df.sample(n=500, random_state=42)
    
    return df


def merge_datasets(data_dir: Path) -> pd.DataFrame:
    """Load and merge all datasets with priority to Indian food datasets."""
    print("Loading datasets...")
    
    df1 = load_indian_food_composition(data_dir)
    print(f"  indian_food_composition: {len(df1)} rows")
    
    df2 = load_indian_food_nutrition_processed(data_dir)
    print(f"  Indian_Food_Nutrition_Processed: {len(df2)} rows")
    
    df3 = load_nutrition_fallback(data_dir)
    print(f"  nutrition (sampled): {len(df3)} rows")
    
    # Concatenate all datasets
    combined = pd.concat([df1, df2, df3], ignore_index=True)
    
    # Remove duplicates, keeping Indian food dataset entries
    # Sort by source priority then drop duplicates
    source_priority = {'indian_food_composition': 0, 'indian_food_nutrition_processed': 1, 'nutrition_fallback': 2}
    combined['priority'] = combined['source'].map(source_priority)
    combined = combined.sort_values('priority')
    combined = combined.drop_duplicates(subset=['Food_Name'], keep='first')
    combined = combined.drop(columns=['priority'])
    
    # Remove empty or invalid entries
    combined = combined[combined['Food_Name'].str.len() > 0]
    combined = combined.dropna(subset=TARGET_COLS)
    
    # Convert to numeric, coercing errors
    for col in TARGET_COLS:
        combined[col] = pd.to_numeric(combined[col], errors='coerce')
    combined = combined.dropna(subset=TARGET_COLS)
    
    print(f"Combined dataset: {len(combined)} unique food items")
    
    return combined


def train_model(df: pd.DataFrame):
    """Train the TF-IDF + Ridge regression pipeline."""
    print("\nTraining nutrition estimator model...")
    
    X = df['Food_Name'].values
    y = df[TARGET_COLS].values
    
    # Build pipeline with TF-IDF vectorizer and multi-output Ridge regression
    # Using char n-grams (2-5) for fuzzy matching of similar food names
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(2, 5),
            max_features=5000,
            lowercase=True,
            strip_accents='unicode'
        )),
        ('regressor', MultiOutputRegressor(
            Ridge(alpha=1.0, random_state=42)
        ))
    ])
    
    # Cross-validation to evaluate model
    print("\nCross-validation (5-fold)...")
    kfold = KFold(n_splits=5, shuffle=True, random_state=42)
    
    # Evaluate MAE for each target
    from sklearn.metrics import mean_absolute_error, make_scorer
    
    mae_scores = {col: [] for col in TARGET_COLS}
    
    for train_idx, val_idx in kfold.split(X):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_val)
        
        for i, col in enumerate(TARGET_COLS):
            mae = mean_absolute_error(y_val[:, i], y_pred[:, i])
            mae_scores[col].append(mae)
    
    print("\nMAE per nutrient (cross-validation):")
    for col in TARGET_COLS:
        mean_mae = np.mean(mae_scores[col])
        std_mae = np.std(mae_scores[col])
        print(f"  {col}: {mean_mae:.2f} ± {std_mae:.2f}")
    
    # Train final model on all data
    print("\nTraining final model on all data...")
    pipeline.fit(X, y)
    
    return pipeline


def save_model(pipeline, output_path: Path):
    """Save trained model to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        'pipeline': pipeline,
        'target_cols': TARGET_COLS,
        'version': '1.0.0'
    }, output_path)
    print(f"\nModel saved to: {output_path}")


def test_predictions(pipeline, test_foods: list):
    """Test model predictions on sample foods."""
    print("\nTest predictions:")
    print("-" * 70)
    
    predictions = pipeline.predict(test_foods)
    
    for food, pred in zip(test_foods, predictions):
        print(f"  {food}:")
        print(f"    Calories: {pred[0]:.1f} | Protein: {pred[1]:.1f}g | Carbs: {pred[2]:.1f}g | Fats: {pred[3]:.1f}g")


def main():
    # Determine paths
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent.parent
    data_dir = backend_dir.parent / 'data set'
    output_path = script_dir / 'nutrition_estimator.joblib'
    
    # Load and merge datasets
    df = merge_datasets(data_dir)
    
    # Train model
    pipeline = train_model(df)
    
    # Save model
    save_model(pipeline, output_path)
    
    # Test with sample foods
    test_foods = [
        'idli',
        'masala dosa',
        'chicken biryani',
        'paneer butter masala',
        'samosa',
        'tea',
        'gulab jamun',
        'dal fry',
        'roti',
        'veg fried rice'
    ]
    test_predictions(pipeline, test_foods)
    
    print("\n✓ Training complete!")


if __name__ == '__main__':
    main()
