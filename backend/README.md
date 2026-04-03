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

- `POST /api/v1/menu/extract`
- `GET /api/v1/menu/search`
- `GET /api/v1/menu/items`
- `GET /api/v1/menu/stats`
- `GET /api/v1/menu/categories`
- `GET /api/v1/menu/cuisines`

### Meals

- `POST /api/v1/meals/generate`
- `GET /api/v1/meals/today`
- `POST /api/v1/meals/substitute`
- `GET /api/v1/meals/recommendations`

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
|   `-- ml/
|-- .env.example
|-- requirements.txt
|-- run.py
`-- README.md
```
