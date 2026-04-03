# Smart Canteen System - Frontend

A React-based frontend for the AI-Powered Smart Canteen System.

## Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

The app will be available at http://localhost:3000

### 3. Build for Production

```bash
npm run build
```

## Features

- **Dashboard**: Health metrics, macro distribution, personalized insights
- **Profile**: Health profile, dietary preferences, budget settings
- **Meal Planner**: AI-generated meal plans (3/7/30 days)
- **Menu Scanner**: Upload menu images for OCR extraction

## Tech Stack

- React 18
- Vite
- Tailwind CSS
- React Router
- Chart.js
- Axios

## Project Structure

```
frontend/
├── src/
│   ├── components/    # Reusable components
│   │   └── Navbar.jsx
│   ├── context/       # React context providers
│   │   └── AuthContext.jsx
│   ├── pages/         # Page components
│   │   ├── Dashboard.jsx
│   │   ├── Login.jsx
│   │   ├── MealPlan.jsx
│   │   ├── MenuUpload.jsx
│   │   ├── Profile.jsx
│   │   └── Register.jsx
│   ├── services/      # API services
│   │   └── api.js
│   ├── App.jsx
│   ├── index.css
│   └── main.jsx
├── index.html
├── package.json
├── tailwind.config.js
└── vite.config.js
```

## API Integration

The frontend proxies API requests to `http://localhost:8000` during development.
Make sure the backend is running before using the app.
