# Smart Canteen Frontend

React frontend for the AI-Powered Smart Canteen System.

## Setup

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Start development server

```bash
npm run dev
```

Frontend runs at the Vite dev URL (usually `http://localhost:5173`).

### 3. Build for production

```bash
npm run build
```

## Features

- Dashboard: health metrics and insights
- Profile: health and dietary preferences
- Meal planner: AI-generated plans
- Menu scanner: image upload and OCR flow

## Tech Stack

- React 18
- Vite
- Tailwind CSS
- React Router
- Chart.js
- Axios

## Project Structure

```text
frontend/
|-- src/
|   |-- components/
|   |-- context/
|   |-- pages/
|   |-- services/
|   |-- App.jsx
|   |-- index.css
|   `-- main.jsx
|-- index.html
|-- package.json
|-- tailwind.config.js
`-- vite.config.js
```

## API Integration

During development, frontend calls are proxied to the backend at `http://localhost:8000`.
Make sure backend is running before using the app.
