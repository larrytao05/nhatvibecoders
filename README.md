# nhatvibecoders

CBC Hackathon SP26 fitness planning app.

The app has two parts:

- `backend/`: Flask API, Postgres, SQLAlchemy, Anthropic/Claude-powered regimen generation.
- `frontend/`: Expo React Native app for iOS, Android, and web.

## Requirements

- Node.js 20+ and npm
- Python 3.11+
- Docker Desktop
- Expo Go on a physical iOS/Android device, or an iOS/Android simulator
- A Claude/Anthropic API key for real AI generation

Your phone and computer must be on the same Wi-Fi network when testing with Expo Go on a physical device.

## 1. Backend Setup

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:

```bash
cat > .env <<'EOF'
DATABASE_URL=postgresql+psycopg2://postgres:postgres@127.0.0.1:5433/nhatvibecoders
CLAUDE_API_KEY=your_api_key_here
ANTHROPIC_API_KEY=your_api_key_here
PORT=5000
FLASK_DEBUG=1
EOF
```

Start Postgres:

```bash
docker compose up -d
```

Start the Flask API:

```bash
source .venv/bin/activate
python app.py
```

The backend should print URLs like:

```text
Running on http://127.0.0.1:5000
Running on http://<your-lan-ip>:5000
```

Leave this terminal running. The API auto-creates database tables on startup.

## 2. Frontend Setup

Open a second terminal from the repository root:

```bash
cd frontend
npm install
```

For iOS simulator, Android emulator, or web on the same computer:

```bash
EXPO_PUBLIC_API_URL=http://127.0.0.1:5000 npx expo start
```

For Expo Go on a physical phone, use your computer's LAN IP from the Flask output:

```bash
EXPO_PUBLIC_API_URL=http://<your-lan-ip>:5000 npx expo start
```

Example:

```bash
EXPO_PUBLIC_API_URL=http://192.168.1.25:5000 npx expo start
```

Leave Expo running, then launch the app:

- Physical iOS/Android: scan the Expo QR code with Expo Go.
- iOS simulator: press `i` in the Expo terminal.
- Android emulator: press `a` in the Expo terminal.
- Web browser: press `w` in the Expo terminal.

If the app still uses an old backend URL after edits, restart Expo with cache cleared:

```bash
npx expo start --clear
```

## 3. Start-To-Finish App Test

Use this checklist to verify the full flow on any device:

1. Open the app and switch to **Sign up**.
2. Create a new username. If it already exists, choose another username or switch to **Log in**.
3. Confirm the app routes to onboarding, starting with biometrics.
4. Enter height, weight, and body fat estimate.
5. Continue through goals and workout preferences.
6. Tap **Generate HTP Regimen**.
7. Watch the Workouts tab. The backend should first create the weekly skeleton, then expand workout days into individual exercises.
8. Open the **Regimen** modal to inspect each day.
9. Select a workout day and confirm individual exercise cards appear.
10. Mark exercise progress and tap **Complete Workout**.
11. Submit workout feedback and accept or reject the suggested next workout.
12. Check the Profile and Progress tabs for saved profile/workout state.

During generation, the backend terminal should show requests like:

```text
POST /users
POST /users/<username>/regimens/skeleton
POST /users/<username>/regimens/<regimen_id>/expand-day
```

## 4. Run Tests

Backend tests:

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

Focused backend API and pipeline tests:

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/test_api.py tests/test_pipeline.py
```

Frontend TypeScript check:

```bash
cd frontend
npx tsc --noEmit
```

## Troubleshooting

If Expo Go cannot reach the backend:

- Use `http://<your-lan-ip>:5000`, not `127.0.0.1`, for physical phones.
- Make sure phone and computer are on the same Wi-Fi network.
- Confirm Flask is running on `0.0.0.0` and prints the same LAN IP.
- Open `http://<your-lan-ip>:5000/` in the phone browser. It should return JSON with `"ok": true`.

If workouts do not generate:

- Check `CLAUDE_API_KEY`/`ANTHROPIC_API_KEY` in `backend/.env`.
- Watch the backend terminal for `regimens/skeleton` and `expand-day` requests.
- Restart Flask after backend code or `.env` changes.
- Reload Expo after frontend code or `EXPO_PUBLIC_API_URL` changes.

If the database gets into a bad local state:

```bash
cd backend
docker compose down -v
docker compose up -d
source .venv/bin/activate
python app.py
```

## Useful Commands

```bash
# Stop Postgres
cd backend && docker compose down

# Wipe Postgres data
cd backend && docker compose down -v

# Start Expo for web only
cd frontend && EXPO_PUBLIC_API_URL=http://127.0.0.1:5000 npm run web

# Start Expo with a clean Metro cache
cd frontend && npx expo start --clear
```
