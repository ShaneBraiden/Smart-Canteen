# Smart Canteen Backend (Flask)

## Setup

### 1. Create and activate a virtual environment

```bash
cd backend
python -m venv venv
# Windows PowerShell
.\\venv\\Scripts\\Activate.ps1
```

### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Python 3.11 or 3.12 is recommended for full OCR support. The OCR stack is configured to use the RTX 4050 GPU when available, and this project currently targets `paddlepaddle-gpu==3.3.1` with CUDA 11.8.

If you are reinstalling the environment, keep the GPU wheel from the Paddle CUDA 11.8 index in place so PaddleOCR can use the RTX 4050 directly. On this workspace, OCR runs with `device='gpu:0'` and falls back to CPU only if the GPU runtime is unavailable.

With Python 3.13, PaddleOCR/OpenCV combinations may fail due to NumPy ABI incompatibility.

### 3. Configure environment

```bash
copy .env.example .env
```

Required variables:

- `MONGODB_URL` (default: `mongodb://localhost:27017`)
- `DATABASE_NAME` (default: `smart_canteen`)
- `SECRET_KEY`
- `DEBUG` (`True` or `False`)

Optional OCR variables:

- `OCR_USE_GPU` (`True` if CUDA is available)
- `OCR_LANG` (`en`, `devanagari`, `ta`, `te`, etc.)

### 4. Start MongoDB

Ensure MongoDB is running locally, or set `MONGODB_URL` to Atlas.

### 5. Run the API

```bash
python run.py
```

Server URL: `http://localhost:8000`

## Behavior Notes

- On first OCR use, PaddleOCR downloads model files.
- OCR uses the RTX 4050 through Paddle GPU. The backend is configured for `device='gpu:0'`, so menu extraction runs on the GPU instead of the CPU when CUDA is available.
- If OCR dependencies are unavailable, non-OCR APIs still work. OCR endpoints return `503` with a clear error.

## Quick API Checks

```bash
# Health
curl http://localhost:8000/health

# Register
curl -X POST http://localhost:8000/api/v1/auth/register -H "Content-Type: application/json" -d "{\"email\":\"test@example.com\",\"username\":\"testuser\",\"password\":\"password123\"}"

# Login (JSON)
curl -X POST http://localhost:8000/api/v1/auth/login/json -H "Content-Type: application/json" -d "{\"email\":\"test@example.com\",\"password\":\"password123\"}"
```

## Main Endpoints

### Authentication

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/login/json`

### User

- `GET /api/v1/users/me`
- `PUT /api/v1/users/me/profile`
- `PUT /api/v1/users/me/dietary-preferences`
- `PUT /api/v1/users/me/budget`
- `PUT /api/v1/users/me/meals`
- `GET /api/v1/users/me/health-metrics`
- `GET /api/v1/users/me/macro-targets`

### Menu and OCR

- `POST /api/v1/menu/extract` — Upload menu image, extract items with OCR, validate nutrition, **save to user's MongoDB**
- `GET /api/v1/menu/scanned` — **Get user's saved scanned menu items**
- `DELETE /api/v1/menu/scanned` — **Clear all scanned menu items**
- `DELETE /api/v1/menu/scanned/<item_name>` — **Remove specific item from scanned menu**
- `GET /api/v1/menu/scanned/stats` — **Get statistics about scanned menu**
- `GET /api/v1/menu/search` — Search food database
- `GET /api/v1/menu/items` — List food items with filters
- `GET /api/v1/menu/stats` — Dataset statistics
- `GET /api/v1/menu/categories` — List categories
- `GET /api/v1/menu/cuisines` — List cuisines
- `POST /api/v1/menu/validate` — Validate batch of food names (ML + database)
- `GET /api/v1/menu/validate/single?food=...` — Validate single food item
- `GET /api/v1/menu/model/status` — Check ML model status

### Meals

- `POST /api/v1/meals/generate` — Generate meal plan from database (legacy)
- `POST /api/v1/meals/generate-from-scanned` — **Generate meal plan from SAVED scanned menu (MongoDB)**
- `POST /api/v1/meals/generate-from-menu` — Generate meal plan from inline menu items (legacy)
- `POST /api/v1/meals/validate-menu` — Validate menu items before planning
- `GET /api/v1/meals/today` — Get today's meal plan
- `POST /api/v1/meals/substitute` — Find item substitutes
- `GET /api/v1/meals/recommendations` — Get quick recommendations

### Recommendations

- `GET /api/v1/recommendations/`
- `POST /api/v1/recommendations/feedback`
- `GET /api/v1/recommendations/similar/<item>`
- `GET /api/v1/recommendations/trending`
- `GET /api/v1/recommendations/personalized-insights`

## Project Layout

```text
backend/
|-- app/
|   |-- api/routes/
|   |-- core/
|   |-- models/
|   |-- schemas/
|   |-- services/
|   |   |-- food_dataset.py      # Food database service
|   |   |-- food_validator.py    # ML-based food validation
|   |   |-- menu_optimizer.py    # Menu-based meal planning with ML
|   |   |-- ocr_service.py       # PaddleOCR integration
|   |   `-- menu_parser.py       # Menu text parsing
|   `-- ml/
|       |-- train_nutrition_estimator.py  # Training script
|       |-- nutrition_estimator.joblib     # Trained model
|       `-- recommender.py                 # Recommendation engine
|-- .env.example
|-- requirements.txt
|-- run.py
`-- README.md
```

## ML Models

### Nutrition Estimator

The nutrition estimator model predicts nutritional values (calories, protein, carbs, fats) from food names. This is used to:
- Estimate nutrition for OCR-scanned foods not in the database
- Provide fallback predictions for unknown items
- Validate and enrich menu extraction results

**Training the model**: See `../docs/ML_TRAINING.md` for detailed instructions.

**Model details**:
- Algorithm: TF-IDF (char n-grams 2-5) + Ridge Multi-Output Regression
- Training data: 1639 unique food items from 3 datasets
- Performance (MAE): Calories ≈96 kcal, Protein ≈3g, Carbs ≈10g, Fats ≈9g
- Location: `backend/app/ml/nutrition_estimator.joblib`

## Meal Planning Workflow

The FDA Smart Canteen uses a **menu-first** workflow where meal plans are generated ONLY from the user's scanned menu:

### Step 1: Scan Menu
```bash
# Upload menu image
curl -X POST http://localhost:8000/api/v1/menu/extract \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@canteen_menu.jpg"
```

This:
1. OCR extracts text from the image (PaddleOCR)
2. ML model validates/predicts nutrition for each item
3. Items are **saved to MongoDB** in `scanned_menus` collection

### Step 2: View Saved Menu
```bash
# Get saved scanned items
curl http://localhost:8000/api/v1/menu/scanned \
  -H "Authorization: Bearer $TOKEN"
```

### Step 3: Generate Meal Plan from Saved Menu
```bash
# Generate meal plan from YOUR scanned menu (not database)
curl -X POST http://localhost:8000/api/v1/meals/generate-from-scanned \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"days": 1}'
```

This uses **only the items you scanned** — not the static food database.

### Key Points
- Each user has their own scanned menu in MongoDB
- Menu items persist until cleared or replaced
- Meal plans are optimized using PuLP linear programming
- Nutrition is either from database match or ML prediction
