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

Connect the frontend to the local Flask API:

```bash
cd frontend
EXPO_PUBLIC_API_URL=http://127.0.0.1:5000 npm start
```

If you are using Expo Go on a physical phone, replace `127.0.0.1` with your computer's LAN IP address, for example:

```bash
cd frontend
EXPO_PUBLIC_API_URL=http://192.168.1.25:5000 npm start
```

The first frontend screen is username-only auth:

- **Log in** calls `GET /users/<username>`.
- **Sign up** calls `POST /users`.
- If a signup username already exists, switch to **Log in**.

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
EXPO_PUBLIC_API_URL=http://127.0.0.1:5000 npm start
```
