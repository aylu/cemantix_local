from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
from difflib import SequenceMatcher
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
WORDS_DIR = Path(os.getenv("WORDS_DIR", str(BASE_DIR / "data" / "cemantix")))
DATA_FILE = Path(os.getenv("WORDS_FILE", str(WORDS_DIR / "words_fr.txt")))
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "cemantix_local.db"))
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "changeme")
PORT = int(os.getenv("PORT", "5000"))


def load_words() -> list[str]:
    words = []
    with DATA_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            w = line.strip().lower()
            if w:
                words.append(w)
    if not words:
        raise RuntimeError("Le dictionnaire local est vide.")
    return words


WORDS = load_words()


def daily_target(words: list[str], day: dt.date | None = None) -> str:
    day = day or dt.date.today()
    index = day.toordinal() % len(words)
    return words[index]


def bigrams(value: str) -> set[str]:
    return {value[i : i + 2] for i in range(max(len(value) - 1, 0))}


def similarity_score(guess: str, target: str) -> int:
    if guess == target:
        return 100

    seq = SequenceMatcher(None, guess, target).ratio()
    g_bi = bigrams(guess)
    t_bi = bigrams(target)
    overlap = len(g_bi & t_bi) / max(len(g_bi | t_bi), 1)

    raw = (0.65 * seq) + (0.35 * overlap)
    return int(round(raw * 100))


def init_db() -> None:
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS guesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                pseudo TEXT,
                guess TEXT NOT NULL,
                score INTEGER NOT NULL,
                target TEXT NOT NULL,
                is_win INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_manual_target() -> str | None:
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = 'manual_target'").fetchone()
    finally:
        conn.close()
    return row[0] if row else None


def set_manual_target(target: str) -> None:
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES ('manual_target', ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (target, dt.datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def active_target() -> str:
    return get_manual_target() or daily_target(WORDS)


def save_guess(pseudo: str | None, guess: str, score: int, target: str, is_win: bool) -> None:
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.execute(
            """
            INSERT INTO guesses (created_at, pseudo, guess, score, target, is_win)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (dt.datetime.utcnow().isoformat(), pseudo, guess, score, target, int(is_win)),
        )
        conn.commit()
    finally:
        conn.close()


def admin_stats() -> dict:
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        total_guesses = conn.execute("SELECT COUNT(*) FROM guesses").fetchone()[0]
        total_wins = conn.execute("SELECT COUNT(*) FROM guesses WHERE is_win = 1").fetchone()[0]
        avg_score = conn.execute("SELECT COALESCE(AVG(score), 0) FROM guesses").fetchone()[0]
        top_players_rows = conn.execute(
            """
            SELECT COALESCE(NULLIF(TRIM(pseudo), ''), 'anonyme') AS player,
                   COUNT(*) AS attempts,
                   MAX(score) AS best_score
            FROM guesses
            GROUP BY player
            ORDER BY best_score DESC, attempts DESC
            LIMIT 10
            """
        ).fetchall()
        recent_rows = conn.execute(
            """
            SELECT created_at, COALESCE(NULLIF(TRIM(pseudo), ''), 'anonyme'), guess, score, is_win
            FROM guesses
            ORDER BY id DESC
            LIMIT 20
            """
        ).fetchall()
        score_distribution = conn.execute(
            """
            SELECT
                CASE
                    WHEN score < 20 THEN '0-19'
                    WHEN score < 40 THEN '20-39'
                    WHEN score < 60 THEN '40-59'
                    WHEN score < 80 THEN '60-79'
                    ELSE '80-100'
                END AS bucket,
                COUNT(*)
            FROM guesses
            GROUP BY bucket
            ORDER BY bucket
            """
        ).fetchall()
        guesses_by_day = conn.execute(
            """
            SELECT substr(created_at, 1, 10) AS day, COUNT(*)
            FROM guesses
            GROUP BY day
            ORDER BY day DESC
            LIMIT 14
            """
        ).fetchall()
    finally:
        conn.close()

    ordered_buckets = ["0-19", "20-39", "40-59", "60-79", "80-100"]
    bucket_map = {bucket: count for bucket, count in score_distribution}

    return {
        "total_guesses": total_guesses,
        "total_wins": total_wins,
        "avg_score": round(float(avg_score), 2),
        "active_target": active_target(),
        "target_source": "manuel" if get_manual_target() else "quotidien",
        "top_players": [
            {"player": r[0], "attempts": r[1], "best_score": r[2]} for r in top_players_rows
        ],
        "recent": [
            {
                "created_at": r[0],
                "pseudo": r[1],
                "guess": r[2],
                "score": r[3],
                "is_win": bool(r[4]),
            }
            for r in recent_rows
        ],
        "score_distribution": [
            {"bucket": bucket, "count": bucket_map.get(bucket, 0)} for bucket in ordered_buckets
        ],
        "guesses_by_day": [
            {"day": row[0], "count": row[1]} for row in reversed(guesses_by_day)
        ],
    }


class CemantixHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/":
            return self._send_file(BASE_DIR / "templates" / "index.html", "text/html; charset=utf-8")
        if parsed.path == "/admin":
            return self._send_file(BASE_DIR / "templates" / "admin.html", "text/html; charset=utf-8")
        if parsed.path.startswith("/static/"):
            file_path = BASE_DIR / parsed.path.lstrip("/")
            content_type = "text/plain; charset=utf-8"
            if file_path.suffix == ".css":
                content_type = "text/css; charset=utf-8"
            elif file_path.suffix == ".js":
                content_type = "application/javascript; charset=utf-8"
            return self._send_file(file_path, content_type)
        if parsed.path == "/api/admin/stats":
            token = parse_qs(parsed.query).get("token", [""])[0]
            if token != ADMIN_TOKEN:
                return self._send_json({"error": "Token admin invalide."}, status=HTTPStatus.FORBIDDEN)
            return self._send_json(admin_stats())

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return self._send_json({"error": "JSON invalide."}, status=HTTPStatus.BAD_REQUEST)

        if parsed.path == "/api/guess":
            guess = (payload.get("guess") or "").strip().lower()
            pseudo = (payload.get("pseudo") or "").strip() or None

            if not guess:
                return self._send_json({"error": "Le mot proposé est vide."}, status=HTTPStatus.BAD_REQUEST)

            target = active_target()
            score = similarity_score(guess, target)
            is_win = guess == target
            save_guess(pseudo, guess, score, target, is_win)

            return self._send_json(
                {
                    "guess": guess,
                    "score": score,
                    "is_win": is_win,
                    "message": "🎉 Bravo, vous avez trouvé le mot du jour !"
                    if is_win
                    else "💪 Continuez !",
                }
            )

        if parsed.path == "/api/admin/target":
            token = (payload.get("token") or "").strip()
            if token != ADMIN_TOKEN:
                return self._send_json({"error": "Token admin invalide."}, status=HTTPStatus.FORBIDDEN)

            new_target = (payload.get("target") or "").strip().lower()
            if new_target not in WORDS:
                return self._send_json(
                    {
                        "error": "Mot invalide : il doit exister dans le dictionnaire Cemantix local."
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
            set_manual_target(new_target)
            return self._send_json(
                {
                    "message": "Mot du jour mis à jour.",
                    "active_target": new_target,
                    "target_source": "manuel",
                }
            )

        self.send_error(HTTPStatus.NOT_FOUND)


def create_server() -> ThreadingHTTPServer:
    init_db()
    return ThreadingHTTPServer(("0.0.0.0", PORT), CemantixHandler)


if __name__ == "__main__":
    server = create_server()
    print(f"Cemantix local démarré sur http://127.0.0.1:{PORT}")
    server.serve_forever()
