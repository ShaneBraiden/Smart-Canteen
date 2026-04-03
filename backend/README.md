# Smart Canteen System - Backend (Flask)

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

Use Python 3.11 or 3.12 for full OCR support. PaddleOCR `2.7.3` depends on
OpenCV `4.6.x`, which can fail on Python 3.13 due to NumPy ABI incompatibility.

**Note on PaddleOCR Installation:**
- PaddleOCR requires `paddlepaddle` (the deep learning framework)
- First-time run will download OCR models automatically (~100MB)
- For GPU support, install `paddlepaddle-gpu` instead of `paddlepaddle`

### 2. Configure Environment

Copy `.env.example` to `.env` and update values:

```bash
cp .env.example .env
```

Required environment variables:
- `MONGODB_URL` - MongoDB connection string (default: `mongodb://localhost:27017`)
- `DATABASE_NAME` - Database name (default: `smart_canteen`)
- `SECRET_KEY` - JWT secret key (generate a secure random string)
- `DEBUG` - Set to `True` for development

Optional OCR settings:
- `OCR_USE_GPU` - Set to `True` if GPU is available
- `OCR_LANG` - OCR language (default: `en` for English)

### 3. Start MongoDB

Make sure MongoDB is running on `localhost:27017`

For Windows, you can:
- Install MongoDB Community Server
- Or use MongoDB Atlas (cloud)

### 4. Run the Server

```bash
# Option 1: Direct Python execution
cd backend
python run.py

# Option 2: Using Flask CLI
cd backend
set FLASK_APP=app.main:app
flask run --port 8000

# Option 3: With auto-reload for development
set FLASK_ENV=development
set FLASK_APP=app.main:app
flask run --port 8000 --reload
```

The server will start at http://localhost:8000

### 5. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"password123"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login/json \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login (form data)
- `POST /api/v1/auth/login/json` - Login (JSON body)

### User Profile (requires JWT token)
- `GET /api/v1/users/me` - Get current user
- `PUT /api/v1/users/me/profile` - Update health profile
- `PUT /api/v1/users/me/dietary-preferences` - Update diet preferences
- `PUT /api/v1/users/me/budget` - Update budget settings
- `PUT /api/v1/users/me/meals` - Update meal configuration
- `GET /api/v1/users/me/health-metrics` - Get BMI, BMR, TDEE
- `GET /api/v1/users/me/macro-targets` - Get protein/carbs/fat targets

### Menu & OCR (requires JWT token)
- `POST /api/v1/menu/extract` - Extract food items from menu image (PaddleOCR)
- `GET /api/v1/menu/search?query=` - Search food items
- `GET /api/v1/menu/items` - List all food items
- `GET /api/v1/menu/stats` - Get dataset statistics
- `GET /api/v1/menu/categories` - Get food categories
- `GET /api/v1/menu/cuisines` - Get cuisines

### Meal Planning (requires JWT token)
- `POST /api/v1/meals/generate?duration=7` - Generate meal plan
- `GET /api/v1/meals/today` - Get today's meal plan
- `POST /api/v1/meals/substitute` - Find budget-friendly substitutes
- `GET /api/v1/meals/recommendations` - Quick meal recommendations

### ML Recommendations (requires JWT token)
- `GET /api/v1/recommendations/` - Get personalized recommendations
- `POST /api/v1/recommendations/feedback` - Submit feedback
- `GET /api/v1/recommendations/similar/<item>` - Find similar items
- `GET /api/v1/recommendations/trending` - Get trending items
- `GET /api/v1/recommendations/personalized-insights` - Get nutrition tips

## Using JWT Token

After login, you'll receive an access token. Include it in requests:

```bash
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── auth.py           # Authentication endpoints
│   │       ├── users.py          # User profile endpoints
│   │       ├── menu.py           # Menu & OCR endpoints
│   │       ├── meals.py          # Meal planning endpoints
│   │       └── recommendations.py # ML recommendations
│   ├── core/
│   │   ├── config.py             # Settings (pydantic-settings)
│   │   ├── database.py           # MongoDB connection (PyMongo)
│   │   └── security.py           # JWT & password hashing
│   ├── models/
│   │   └── user.py               # User model
│   ├── schemas/
│   │   └── user.py               # Pydantic schemas
│   ├── services/
│   │   ├── health_calculator.py  # BMI/BMR/TDEE calculations
│   │   ├── user_service.py       # User operations
│   │   ├── food_dataset.py       # Food data management
│   │   ├── menu_parser.py        # Menu text parsing
│   │   ├── ocr_service.py        # PaddleOCR (multi-language)
│   │   └── optimizer.py          # Budget optimization (PuLP)
│   ├── ml/
│   │   └── recommender.py        # ML recommendation engine
│   └── main.py                   # Flask application
├── run.py                        # Entry point script
├── requirements.txt
├── .env
└── README.md
```

## Tech Stack

- **Framework**: Flask 3.0
- **Database**: MongoDB (PyMongo)
- **Authentication**: Flask-JWT-Extended
- **Validation**: Pydantic v2
- **ML**: scikit-learn (Random Forest)
- **Optimization**: PuLP (Linear Programming)
- **OCR**: PaddleOCR (multi-language: English + Indian languages)
- **Image Processing**: OpenCV

## OCR Language Support

PaddleOCR supports multiple Indian languages:
- English (`en`)
- Hindi (`hi` / `devanagari`)
- Tamil (`ta`)
- Telugu (`te`)
- Kannada (`kn`)
- Malayalam (`ml`)
- Bengali (`bn`)
- Gujarati (`gu`)

The default is English. For Hindi menus, set `OCR_LANG=devanagari` in `.env`.
