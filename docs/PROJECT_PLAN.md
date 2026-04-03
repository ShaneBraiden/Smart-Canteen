# AI-Powered Smart Canteen System
## Project Plan & Architecture

---

## 🎯 Project Overview

**Title:** AI-Powered Smart Canteen System with Personalized Diet & Budget Optimization

**Objective:** Build a full-stack web application that:
- Extracts food items/prices from canteen menu images (OCR)
- Analyzes nutritional values from a food composition dataset
- Calculates health metrics (BMI, BMR, Caloric Needs)
- Uses ML and optimization algorithms for personalized, budget-friendly diet plans

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React.js, Tailwind CSS, Chart.js, Vite |
| **Backend** | Python (Flask 3.0) |
| **AI/ML** | scikit-learn (Random Forest), PuLP (LP) |
| **Computer Vision** | OpenCV, PaddleOCR (multi-language) |
| **Database** | MongoDB (PyMongo) |
| **Authentication** | Flask-JWT-Extended |

---

## 📦 Module Breakdown

### Module 1: User Input & Profile Module ✅
- User registration/authentication (JWT)
- Profile data collection (age, gender, height, weight)
- Health preferences (activity level, goals)
- Dietary constraints (veg/non-veg, allergies)
- Budget constraints (daily/weekly/monthly)

### Module 2: Health Calculation Engine ✅
- BMI Calculator with categorization
- BMR calculation (Mifflin-St Jeor equation)
- TDEE (Total Daily Energy Expenditure) calculation
- Goal-based caloric adjustment

### Module 3: Menu Image Processing & OCR ✅
- Image upload and preprocessing (OpenCV)
- Text extraction (PaddleOCR - multi-language)
- Dish name and price parsing (Regex)
- Confidence scoring for extractions

### Module 4: Food & Nutrition Mapping ✅
- Dataset loading and indexing (140+ items)
- Fuzzy matching for food items (FuzzyWuzzy)
- Nutritional data retrieval
- Allergen flagging

### Module 5: Budget Optimization Engine ✅
- Linear Programming with PuLP
- Cost efficiency scoring
- Smart substitution logic
- Constraint satisfaction (budget, calories, macros)

### Module 6: ML Recommendation Engine ✅
- User preference learning
- Random Forest for meal scoring
- Hybrid system (40% rules + 60% ML)
- Feedback loop integration

### Module 7: Meal Planning & Dashboard ✅
- Multi-day meal plan generation (3/7/30 days)
- Cuisine variation logic
- Visual dashboard (Chart.js)
- Budget tracking UI

---

## 📂 Project Structure

```
FDA/
├── frontend/                 # React.js application
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Route pages
│   │   ├── services/        # API client
│   │   ├── context/         # Auth context
│   │   └── hooks/           # Custom hooks
│   ├── package.json
│   └── vite.config.js
├── backend/                  # Flask application
│   ├── app/
│   │   ├── api/routes/      # REST endpoints
│   │   ├── core/            # Config, DB, security
│   │   ├── models/          # MongoDB models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   └── ml/              # ML recommender
│   ├── run.py
│   └── requirements.txt
├── data set/                 # Static food composition data
│   └── indian_food_composition.csv
├── docs/                     # Documentation
│   ├── PROJECT_PLAN.md
│   └── TODO.md
└── README.md
```

---

## 🔄 Development Phases

### Phase 0: Workspace & Data Setup ✅
- [x] Create project directories
- [x] Generate food composition dataset (140+ items)
- [x] Initialize documentation

### Phase 1: Foundation (Backend Core) ✅
- [x] Flask project setup
- [x] MongoDB connection (PyMongo)
- [x] User authentication (JWT)
- [x] Health calculation endpoints

### Phase 2: Data & OCR ✅
- [x] Food dataset integration
- [x] OCR pipeline implementation (PaddleOCR)
- [x] Food-nutrition mapping service
- [x] Multi-language support (En + Indian languages)

### Phase 3: Optimization & ML ✅
- [x] Budget optimization engine (PuLP)
- [x] ML recommendation system (Random Forest)
- [x] Substitution logic

### Phase 4: Frontend & Integration ✅
- [x] React app setup (Vite + Tailwind)
- [x] UI components
- [x] API integration
- [x] Dashboard & visualizations

### Phase 5: Testing & Deployment 🔄
- [ ] Unit tests
- [ ] Integration tests
- [ ] Docker containerization
- [ ] Deployment

---

## ✅ Decisions Made

| Question | Decision |
|----------|----------|
| **Database** | MongoDB (Document-based, PyMongo) |
| **Authentication** | Simple JWT (Flask-JWT-Extended) |
| **OCR Engine** | PaddleOCR (multi-language support) |
| **Menu Language** | English + Indian languages |
| **Meal Frequency** | Flexible (user configurable) |
| **Framework** | Flask 3.0 (converted from FastAPI) |

---

## 📊 Success Metrics

- OCR accuracy > 85% for menu extraction
- Meal plans within ±5% of budget target
- User satisfaction score for recommendations
- API response time < 500ms for meal generation

---

## 🔧 API Endpoints Summary

| Category | Count | Status |
|----------|-------|--------|
| Authentication | 3 | ✅ |
| User Profile | 7 | ✅ |
| Menu & OCR | 6 | ✅ |
| Meal Planning | 4 | ✅ |
| ML Recommendations | 5 | ✅ |
| **Total** | **25** | ✅ |

---

*Document Version: 2.0*
*Last Updated: April 2026*
*Status: Development Complete, Testing Pending*
