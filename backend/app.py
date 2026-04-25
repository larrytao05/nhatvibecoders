import os

import flask
from dotenv import load_dotenv

from db import User, get_session, init_db


load_dotenv()

app = flask.Flask(__name__)


@app.get("/")
def home():
    return {"ok": True, "service": "nhatvibecoders-backend"}


@app.post("/users")
def create_user():
    payload = flask.request.get_json(silent=True) or {}
    username = payload.get("username")
    current_weight = payload.get("current_weight")

    if not isinstance(username, str) or not username.strip():
        return {"error": "username is required"}, 400

    username = username.strip()

    with get_session() as session:
        existing = session.query(User).filter_by(username=username).first()
        if existing is not None:
            return {"error": "username already exists"}, 409

        user = User(username=username, current_weight=current_weight)
        session.add(user)
        session.commit()

        return {
            "id": user.id,
            "username": user.username,
            "current_weight": user.current_weight,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }, 201


@app.get("/users/<username>")
def get_user(username: str):
    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user is None:
            return {"error": "not found"}, 404

        return {
            "id": user.id,
            "username": user.username,
            "current_weight": user.current_weight,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }


@app.patch("/users/<username>")
def update_user(username: str):
    payload = flask.request.get_json(silent=True) or {}
    current_weight = payload.get("current_weight")

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user is None:
            return {"error": "not found"}, 404

        if "current_weight" in payload:
            user.current_weight = current_weight

        session.commit()

        return {
            "id": user.id,
            "username": user.username,
            "current_weight": user.current_weight,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }


if __name__ == "__main__":
    init_db()
    app.run(debug=bool(int(os.getenv("FLASK_DEBUG", "1"))))