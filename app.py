from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3, os

app = Flask(__name__)
app.secret_key = "secretkey"

UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ---------------- DATABASE ----------------
def get_db():
    return sqlite3.connect("database.db")

def init_db():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)
    cursor.execute("""
CREATE TABLE IF NOT EXISTS resources(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    subjectName TEXT,
    semester TEXT,
    filename TEXT,
    branch TEXT,
    batch TEXT,
    note_type TEXT,
    status TEXT,
    uploaded_by TEXT
)
""")

    db.commit()
    db.close()

init_db()

# ---------------- USER CLASS ----------------
class User(UserMixin):
    def __init__(self, id, name, email, password):
        self.id = id
        self.name = name
        self.email = email
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cur.fetchone()
    if user:
        return User(*user)
    return None

# ---------------- ROUTES ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cur.fetchone()

        if user and check_password_hash(user[3], password):
            login_user(User(*user))
            return redirect("/dashboard")
        flash("Invalid credentials")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        db = get_db()
        cur = db.cursor()
        try:
            cur.execute("INSERT INTO users VALUES (NULL,?,?,?)", (name, email, password))
            db.commit()
            return redirect("/")
        except:
            flash("Email already exists")

    return render_template("register.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":

        title = request.form["title"]
        subjectName = request.form["subjectName"]
        semester = request.form["semester"]
        branch = request.form["branch"]
        batch = request.form["batch"]
        note_type = request.form["note_type"]

        file = request.files["file"]
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        # Verification logic
        ask_verification = "ask_verification" in request.form
        if note_type == "Question Bank":
            status = "pending" if ask_verification else "approved"
        else:
            status = "approved"

        db = get_db()
        cur = db.cursor()
        cur.execute("""
INSERT INTO resources (
    title,
    subjectName,
    semester,
    filename,
    branch,
    batch,
    note_type,
    status,
    uploaded_by
)
VALUES (?,?,?,?,?,?,?,?,?)
""", (
    title,
    subjectName,
    semester,
    filename,
    branch,
    batch,
    note_type,
    status,
    current_user.name
))

        db.commit()

        if status == "pending":
            flash("Uploaded successfully. Waiting for teacher approval.")
        else:
            flash("Uploaded successfully.")

        return redirect("/upload")

    return render_template("upload.html")


@app.route("/resources")
@login_required
def resources():
    branch = request.args.get("branch")
    semester = request.args.get("semester")
    note_type = request.args.get("note_type")

    query = "SELECT * FROM resources WHERE status IN ('approved','verified')"
    params = []

    if branch:
        query += " AND branch=?"
        params.append(branch)

    if semester:
        query += " AND semester=?"
        params.append(semester)

    if note_type:
        query += " AND note_type=?"
        params.append(note_type)

    db = get_db()
    cur = db.cursor()
    cur.execute(query, params)
    data = cur.fetchall()

    return render_template("resources.html", data=data)


@app.route("/download/<filename>")
@login_required
def download(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
