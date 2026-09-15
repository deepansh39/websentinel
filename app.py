import os

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)
from database import (
    create_user,
    get_user_by_email,
    get_scan_history,
    init_db,
)

from database import (
    get_scan_history,
    init_db,
)

from scanner.scan_manager import (
    create_scan,
    get_scan,
)


app = Flask(__name__)

app.secret_key = "dev-secret-change-later"


# Initialize SQLite database
init_db()


# =========================================================
# LANDING PAGE
# =========================================================

@app.route("/")
def index():
    return render_template("index.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        user = get_user_by_email(
            email
        )

        if user is None:

            return render_template(
                "login.html",
                error="Invalid email or password.",
            )

        if not check_password_hash(
            user["password_hash"],
            password,
        ):

            return render_template(
                "login.html",
                error="Invalid email or password.",
            )

        session["logged_in"] = True

        session["user_id"] = user["id"]

        session["user_email"] = user["email"]

        session["user_name"] = user["name"]

        return redirect(
            url_for("dashboard")
        )

    return render_template(
        "login.html"
    )
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "GET":
        return render_template("signup.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    # Basic validation
    if not name:
        return render_template(
            "signup.html",
            error="Please enter your full name.",
        )

    if not email:
        return render_template(
            "signup.html",
            error="Please enter a valid email address.",
        )

    if len(password) < 8:
        return render_template(
            "signup.html",
            error="Password must be at least 8 characters.",
        )

    if password != confirm_password:
        return render_template(
            "signup.html",
            error="Passwords do not match.",
        )

    # Check existing account
    existing_user = get_user_by_email(email)

    if existing_user:
        return render_template(
            "signup.html",
            error="An account with this email already exists.",
        )

    # Hash password
    password_hash = generate_password_hash(
        password,
        method="pbkdf2:sha256",
    )

    # Create account
    user_id = create_user(
        name=name,
        email=email,
        password_hash=password_hash,
    )

    if user_id is None:
        return render_template(
            "signup.html",
            error="Unable to create account. Please try again.",
        )

    # Account created successfully
    return redirect(
        url_for(
            "login",
            registered="1",
        )
    )
# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if not session.get("logged_in"):
        return redirect(
            url_for("login")
        )

    scans = get_scan_history(
        limit=20
    )

    return render_template(
        "dashboard.html",
        scans=scans,
    )


# =========================================================
# START SCAN
# =========================================================

@app.route("/scan", methods=["POST"])
def start_scan():

    if not session.get("logged_in"):
        return redirect(
            url_for("login")
        )

    target = request.form.get(
        "target",
        ""
    ).strip()

    if not target:

        return render_template(
            "dashboard.html",
            scans=get_scan_history(
                limit=20
            ),
            error="Please enter a target URL.",
        )

    try:

        scan_id = create_scan(
            target
        )

        return redirect(
            url_for(
                "scan_status",
                scan_id=scan_id,
            )
        )

    except Exception as exc:

        return render_template(
            "dashboard.html",
            scans=get_scan_history(
                limit=20
            ),
            error=str(exc),
        )


# =========================================================
# SCAN STATUS PAGE
# =========================================================

@app.route("/scan/<scan_id>")
def scan_status(scan_id):

    if not session.get("logged_in"):
        return redirect(
            url_for("login")
        )

    scan = get_scan(
        scan_id
    )

    if scan is None:

        return (
            "Scan not found",
            404,
        )

    return render_template(
        "scan_status.html",
        scan=scan,
    )


# =========================================================
# SCAN STATUS API
# =========================================================

@app.route("/api/scan/<scan_id>")
def scan_api(scan_id):

    if not session.get("logged_in"):

        return jsonify(
            {
                "error": "Unauthorized"
            }
        ), 401

    scan = get_scan(
        scan_id
    )

    if scan is None:

        return jsonify(
            {
                "error": "Scan not found"
            }
        ), 404

    return jsonify(scan)


# =========================================================
# RESULTS PAGE
# =========================================================

@app.route("/results/<scan_id>")
def results(scan_id):

    if not session.get("logged_in"):
        return redirect(
            url_for("login")
        )

    scan = get_scan(
        scan_id
    )

    if scan is None:

        return (
            "Scan not found",
            404,
        )

    return render_template(
        "results.html",
        scan=scan,
        findings=scan.get(
            "findings",
            [],
        ),
    )


# =========================================================
# DOWNLOAD ZAP REPORT
# =========================================================

@app.route(
    "/reports/<scan_id>/<report_type>"
)
def download_report(
    scan_id,
    report_type,
):

    if not session.get("logged_in"):
        return redirect(
            url_for("login")
        )

    scan = get_scan(
        scan_id
    )

    if scan is None:

        return (
            "Scan not found",
            404,
        )

    result = scan.get(
        "result"
    )

    if not result:

        return (
            "Scan report is not available",
            404,
        )

    # Select requested report
    if report_type == "json":

        report_path = result.get(
            "json_report"
        )

    elif report_type == "html":

        report_path = result.get(
            "html_report"
        )

    else:

        return (
            "Invalid report type",
            400,
        )

    if not report_path:

        return (
            "Report not available",
            404,
        )

    report_path = os.path.abspath(
        report_path
    )

    if not os.path.exists(
        report_path
    ):

        return (
            "Report file not found",
            404,
        )

    return send_file(
        report_path,
        as_attachment=True,
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(
        debug=True
    )