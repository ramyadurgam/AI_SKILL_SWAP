"""
AI SkillSwap — simple backend (Python standard library only, no frameworks).

Run:
    python3 backend.py
Serves on http://localhost:8000

Endpoints:
    GET  /students        -> list onboarded students
    POST /students         -> add a student  {name, teach, teach_level, learn, learn_level, availability}
    GET  /match             -> run AI matching over current students
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from difflib import SequenceMatcher

LEVELS = {"beginner": 1, "intermediate": 2, "advanced": 3}

# in-memory "database"
students = []


def similarity(a, b):
    a, b = a.lower().strip(), b.lower().strip()
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.9
    return SequenceMatcher(None, a, b).ratio()


def teaches(student, skill_name):
    return similarity(student["teach"], skill_name) > 0.8


def score(learner, teacher):
    reasons = []
    pts = 0
    sim = similarity(learner["learn"], teacher["teach"])
    pts += sim * 40
    reasons.append(f"skill match {sim:.0%}")

    if LEVELS[teacher["teach_level"]] >= LEVELS[learner["learn_level"]]:
        pts += 20
        reasons.append(f"teacher is {teacher['teach_level']}, covers {learner['learn_level']} learner")
    else:
        pts += 5
        reasons.append(f"teacher is only {teacher['teach_level']}")

    overlap = set(learner["availability"]) & set(teacher["availability"])
    if overlap:
        pts += 15
        reasons.append("shared availability: " + ", ".join(sorted(overlap)))
    else:
        reasons.append("no shared availability")

    if teaches(learner, teacher["learn"]):
        pts += 15
        reasons.append(f"mutual swap: {teacher['name']} wants '{teacher['learn']}' which {learner['name']} teaches")

    return round(pts, 1), reasons


def find_matches():
    result = []
    for learner in students:
        candidates = []
        for teacher in students:
            if teacher["name"] == learner["name"]:
                continue
            if teaches(teacher, learner["learn"]):
                pts, reasons = score(learner, teacher)
                candidates.append({"teacher": teacher["name"], "score": pts, "reasons": reasons})
        candidates.sort(key=lambda c: c["score"], reverse=True)
        result.append({"learner": learner["name"], "wants": learner["learn"], "candidates": candidates})
    return result


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, {})

    def do_GET(self):
        if self.path == "/students":
            self._send(200, {"students": students})
        elif self.path == "/match":
            self._send(200, {"matches": find_matches()})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/students":
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length))
            students.append(data)
            self._send(201, {"ok": True, "total": len(students)})
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        print("[server]", fmt % args)


if __name__ == "__main__":
    print("AI SkillSwap backend running at http://localhost:8000")
    HTTPServer(("localhost", 8000), Handler).serve_forever()
