"""Magnus dealer CRM. SQLite, seeded from the spreadsheet export."""
import csv
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get("DATABASE_PATH", ROOT / "crm.db"))
DATA = ROOT / "data" if (ROOT / "data" / "Companies.csv").exists() else ROOT
TEMPLATE_DIR = ROOT / "templates" if (ROOT / "templates" / "index.html").exists() else ROOT
app = Flask(__name__, template_folder=str(TEMPLATE_DIR))


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    conn = db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS companies (
            name TEXT PRIMARY KEY,
            type TEXT, network TEXT, status TEXT,
            phone TEXT, email TEXT, contact TEXT, notes TEXT
        );
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT, contact TEXT, type TEXT,
            summary TEXT, logged_on TEXT, logged_by TEXT
        );
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT, contact TEXT, reminder TEXT,
            due TEXT, status TEXT
        );
        CREATE TABLE IF NOT EXISTS prospects (
            name TEXT PRIMARY KEY,
            phone TEXT, contact TEXT, email TEXT,
            outcome TEXT, notes TEXT, last_contact TEXT
        );
        """
    )
    if conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0] == 0 and (DATA / "Companies.csv").exists():
        seed(conn)
    conn.commit()
    conn.close()


def seed(conn):
    with open(DATA / "Companies.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            conn.execute(
                "INSERT OR IGNORE INTO companies VALUES (?,?,?,?,?,?,?,?)",
                (r["Company Name"], r["Type"], r["Buy Group Network"], r["Status"] or "Active",
                 r["Phone"], r["Email"], r["Primary Contact"], r["Notes"]),
            )
    with open(DATA / "Activity_Log.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            conn.execute(
                "INSERT INTO activity (company, contact, type, summary, logged_on, logged_by) VALUES (?,?,?,?,?,?)",
                (r["Company"], r["Contact"], r["Type"], r["Summary"], r["Date"], r["Logged By"]),
            )
    with open(DATA / "Reminders.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            conn.execute(
                "INSERT INTO reminders (company, contact, reminder, due, status) VALUES (?,?,?,?,?)",
                (r["Company"], r["Contact"], r["Reminder"], r["Due Date"], r["Status"] or "Open"),
            )
    if (DATA / "Prospects.csv").exists():
        with open(DATA / "Prospects.csv", newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                conn.execute(
                    "INSERT OR IGNORE INTO prospects VALUES (?,?,?,?,?,?,?)",
                    (r["Company Name"], r["Phone"], r["Contact"], "", r["Outcome"], r["Notes"], r["Last Contact"]),
                )


@app.route("/")
def home():
    today = date.today().isoformat()
    q = (request.args.get("q") or "").strip()
    conn = db()
    sql = """
        SELECT c.*, 
          (SELECT logged_on FROM activity a WHERE a.company = c.name AND a.logged_on != '' ORDER BY logged_on DESC LIMIT 1) AS last_on,
          (SELECT type || ': ' || summary FROM activity a WHERE a.company = c.name ORDER BY COALESCE(NULLIF(logged_on,''), '0000') DESC, id DESC LIMIT 1) AS last_note
        FROM companies c
        WHERE c.status != 'Inactive'
    """
    args = []
    if q:
        sql += " AND (c.name LIKE ? OR c.contact LIKE ? OR c.email LIKE ?)"
        args = [f"%{q}%"] * 3
    sql += " ORDER BY CASE WHEN last_on IS NULL OR last_on = '' THEN 0 ELSE 1 END, last_on ASC, c.name LIMIT 200"
    rows = conn.execute(sql, args).fetchall()
    due = conn.execute(
        "SELECT * FROM reminders WHERE status = 'Open' AND due != '' AND due <= ? ORDER BY due LIMIT 25",
        (today,),
    ).fetchall()
    prospects = conn.execute("SELECT * FROM prospects WHERE outcome != 'Not Interested'").fetchall()
    conn.close()
    return render_template("index.html", rows=rows, due=due, prospects=prospects, q=q, today=today)


@app.route("/log", methods=["POST"])
def log():
    company = request.form["company"].strip()
    summary = request.form["summary"].strip()
    kind = request.form.get("type") or "Call"
    if company and summary:
        conn = db()
        conn.execute(
            "INSERT INTO activity (company, contact, type, summary, logged_on, logged_by) VALUES (?,?,?,?,?,?)",
            (company, request.form.get("contact", ""), kind, summary, date.today().isoformat(), "Brent Parker"),
        )
        conn.execute("INSERT OR IGNORE INTO companies (name, type, status) VALUES (?,?,?)", (company, "Prospect", "Prospect"))
        conn.commit()
        conn.close()
    return redirect(url_for("home"))


@app.route("/reminder/<int:rid>/done", methods=["POST"])
def done(rid):
    conn = db()
    conn.execute("UPDATE reminders SET status = 'Done' WHERE id = ?", (rid,))
    conn.commit()
    conn.close()
    return redirect(url_for("home"))


init()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
