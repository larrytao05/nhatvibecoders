# nhatvibecoders
CBC Hackathon SP26

## Requirements

- Node.js 20.19.4+ recommended for Expo / React Native.
- npm
- Python 3
- Docker Desktop for local Postgres
- Expo Go on your phone, or an iOS / Android simulator

## Frontend

React Native (Expo) lives in `frontend/`.

Install dependencies:

```bash
cd frontend
npm install
```

Start Expo:

```bash
cd frontend
npm start
```

Useful Expo commands:

```bash
npm run ios
npm run android
npm run web
npx expo start --clear
```

Type-check the frontend:

```bash
cd frontend
npx tsc --noEmit
```

## Backend

Flask + Postgres lives in `backend/` (see `backend/README.md`).

Start Postgres:

```bash
cd backend
docker compose up -d
```

Create the backend environment:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Run the Flask API:

```bash
cd backend
source .venv/bin/activate
python app.py
```

Stop Postgres:

```bash
cd backend
docker compose down
```

Wipe local Postgres data:

```bash
cd backend
docker compose down -v
```

## Quick Start

Run these in separate terminals:

```bash
cd backend
docker compose up -d
source .venv/bin/activate
python app.py
```

```bash
cd frontend
npm install
npm start
```
