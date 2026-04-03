# AI-Powered Smart Canteen System

A full-stack web application that extracts food items from canteen menu images, analyzes nutrition, and generates personalized budget-friendly meal plans.

## Features

- JWT-based authentication
- Health profile with BMI, BMR, and TDEE calculations
- Menu OCR with PaddleOCR (multi-language)
- Indian food nutrition database
- Budget-aware meal optimization with linear programming
- Personalized recommendations

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

- Auth: `/api/v1/auth/*`
- Users: `/api/v1/users/*`
- Menu/OCR: `/api/v1/menu/*`
- Meals: `/api/v1/meals/*`
- Recommendations: `/api/v1/recommendations/*`

See backend docs for full endpoint details: `backend/README.md`.

## License

MIT
