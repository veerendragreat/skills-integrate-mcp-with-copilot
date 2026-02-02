"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

import csv
from typing import List

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


# Persistence setup
DATA_FILE = current_dir / "results.txt"


def load_persistence():
    """Load participants from DATA_FILE (CSV: activity,email)"""
    if not DATA_FILE.exists():
        return
    try:
        with DATA_FILE.open("r", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 2:
                    continue
                activity_name, email = row[0], row[1]
                if activity_name in activities:
                    # avoid duplicates
                    if email not in activities[activity_name]["participants"]:
                        activities[activity_name]["participants"].append(email)
    except Exception as e:
        # If loading fails, log to console but continue with in-memory data
        print(f"Failed to load persistence from {DATA_FILE}: {e}")


def save_persistence():
    """Save participants to DATA_FILE as CSV rows: activity,email"""
    try:
        with DATA_FILE.open("w", newline="") as f:
            writer = csv.writer(f)
            for name, info in activities.items():
                participants: List[str] = info.get("participants", [])
                for email in participants:
                    writer.writerow([name, email])
    except Exception as e:
        # bubble up as runtime error so endpoints can report failure
        raise RuntimeError(f"Failed to save persistence: {e}")


# Load persistence at startup
load_persistence()

# --- Students persistence and registry ---
STUDENTS_FILE = current_dir / "students.csv"

class Student(
    # lightweight dict-like model for older Python versions without pydantic
):
    def __init__(self, student_id: str, name: str, email: str):
        self.student_id = student_id
        self.name = name
        self.email = email

    def dict(self):
        return {"student_id": self.student_id, "name": self.name, "email": self.email}


# In-memory students registry (student_id -> Student)
students = {}
STUDENT_CAPACITY = 100


def load_students():
    """Load student registry from STUDENTS_FILE (CSV: student_id,name,email)"""
    if not STUDENTS_FILE.exists():
        return
    try:
        with STUDENTS_FILE.open("r", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 3:
                    continue
                sid, name, email = row[0], row[1], row[2]
                students[sid] = Student(sid, name, email)
    except Exception as e:
        print(f"Failed to load students from {STUDENTS_FILE}: {e}")


def save_students():
    """Save student registry to STUDENTS_FILE (CSV: student_id,name,email)"""
    try:
        with STUDENTS_FILE.open("w", newline="") as f:
            writer = csv.writer(f)
            for sid, student in students.items():
                writer.writerow([student.student_id, student.name, student.email])
    except Exception as e:
        raise RuntimeError(f"Failed to save students: {e}")


# Load persistence at startup
load_students()


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Check activity capacity
    if len(activity["participants"]) >= activity.get("max_participants", 0):
        raise HTTPException(status_code=400, detail="Activity is full")

    # Add student
    activity["participants"].append(email)
    try:
        save_persistence()
    except RuntimeError as e:
        # If saving fails, remove the added participant to keep consistency
        activity["participants"].remove(email)
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    try:
        save_persistence()
    except RuntimeError as e:
        # If saving fails, re-add the participant to keep consistency
        activity["participants"].append(email)
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": f"Unregistered {email} from {activity_name}"}


# --- Student registration endpoints ---
@app.post("/students")
def register_student(student_id: str, name: str, email: str):
    """Register a new student. Enforces unique student_id and capacity limit."""
    # Capacity check
    if len(students) >= STUDENT_CAPACITY:
        raise HTTPException(status_code=400, detail="Student registry is full")

    # Unique ID check
    if student_id in students:
        raise HTTPException(status_code=400, detail="Student ID already registered")

    # Prevent duplicate emails (optional safety)
    if any(s.email == email for s in students.values()):
        raise HTTPException(status_code=400, detail="Email already registered")

    students[student_id] = Student(student_id, name, email)
    try:
        save_students()
    except RuntimeError as e:
        # Rollback
        del students[student_id]
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": f"Registered student {student_id}"}


@app.get("/students/{student_id}")
def get_student(student_id: str):
    if student_id not in students:
        raise HTTPException(status_code=404, detail="Student not found")
    s = students[student_id]
    return {"student_id": s.student_id, "name": s.name, "email": s.email}


@app.get("/students")
def list_students():
    """Return roster sorted alphabetically by name"""
    roster = sorted(list(students.values()), key=lambda s: s.name)
    return [{"student_id": s.student_id, "name": s.name, "email": s.email} for s in roster]


@app.get("/students/available_seats")
def available_seats():
    return {"available_seats": STUDENT_CAPACITY - len(students)}
