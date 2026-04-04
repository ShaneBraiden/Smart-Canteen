# AI-Powered Smart Canteen System

A full-stack web application that extracts food items from canteen menu images, analyzes nutrition, and generates personalized budget-friendly meal plans.

## Features

- **JWT-based authentication** — Secure user registration and login
- **Health profile** — BMI, BMR, and TDEE calculations
- **Menu OCR** — PaddleOCR (multi-language support for English + Indian languages)
- **ML-powered nutrition estimation** — Predicts nutrition for unknown foods using TF-IDF + Ridge regression
- **Food validation** — Validates OCR-scanned foods against 1600+ item database with fuzzy matching
- **Indian food nutrition database** — 143 canteen items + 1014 processed dishes
- **Budget-aware meal optimization** — Linear programming with PuLP
- **Personalized recommendations** — ML-based food suggestions

## Tech Stack

- Frontend: React, Tailwind CSS, Chart.js
- Backend: Flask 3, Python
- Database: MongoDB
- ML/Optimization: scikit-learn, PuLP
- OCR: PaddleOCR + OpenCV, using the RTX 4050 GPU on supported Windows/CUDA 11.8 setups

## Quick Start

### Prerequisites

- Python 3.11 or 3.12 (recommended for OCR compatibility)
- Node.js 18+
- MongoDB (local or Atlas)

### Backend

```bash
cd backend
python -m venv venv
# Windows PowerShell
.\\venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python run.py
```

Backend runs at `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at the Vite dev URL (usually `http://localhost:5173`).

## Project Structure

```text
FDA/
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |-- core/
|   |   |-- models/
|   |   |-- schemas/
|   |   |-- services/
|   |   `-- ml/
|   |-- requirements.txt
|   `-- run.py
|-- frontend/
|   |-- src/
|   `-- package.json
|-- data set/
`-- docs/
```

## API Overview

- **Auth**: `/api/v1/auth/*` — Register, login, token management
- **Users**: `/api/v1/users/*` — Profile, dietary preferences, health metrics
- **Menu/OCR**: `/api/v1/menu/*` — Image upload, OCR extraction, food validation
- **Meals**: `/api/v1/meals/*` — Meal plan generation, substitutions
- **Recommendations**: `/api/v1/recommendations/*` — Personalized food suggestions

See backend docs for full endpoint details: `backend/README.md`.

## ML Models

This system uses machine learning models for:

1. **Nutrition Estimator** (`nutrition_estimator.joblib`)
   - Predicts calories, protein, carbs, fats from food names
   - TF-IDF vectorization + Ridge regression
   - Trained on 1639 food items from 3 datasets
   - MAE: Calories ≈96 kcal, Protein ≈3g, Carbs ≈10g, Fats ≈9g

2. **Food Validator** (validation service)
   - Validates OCR-scanned food names
   - Combines fuzzy matching + ML predictions
   - 3 modes: database match, hybrid, ML prediction

**Training the ML model**: See `docs/ML_TRAINING.md` for instructions.

## Datasets

Located in `data set/`:
- `indian_food_composition.csv` — 143 canteen items (primary)
- `Indian_Food_Nutrition_Processed.csv` — 1014 detailed Indian dishes
- `nutrition.csv` — 8789 general nutrition reference (fallback)

## License

MIT
