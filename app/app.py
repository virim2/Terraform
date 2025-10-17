import os
import re
import pymysql
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import random

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambia_esto_en_produccion")

# DB config desde variables de entorno
DB_HOST = os.environ.get("MYSQL_HOST", "mysql")
DB_USER = os.environ.get("MYSQL_USER", "appuser")
DB_PASSWORD = os.environ.get("MYSQL_PASSWORD", "apppassword")
DB_NAME = os.environ.get("MYSQL_DATABASE", "appdb")
DB_PORT = int(os.environ.get("MYSQL_PORT", 3306))

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
        charset='utf8mb4'
    )

def valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
@login_required
def home():
    value = random.randint(0, 100)
    user_name = session.get("user_name")
    return render_template("index.html", random_value=value, user_name=user_name)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        password = request.form.get("password", "")
        telefono = request.form.get("telefono", "").strip()
        correo = request.form.get("correo", "").strip().lower()

        if not nombre or not password or not correo:
            flash("Nombre, correo y contraseña son obligatorios.", "danger")
            return render_template("register.html")

        if not valid_email(correo):
            flash("Formato de correo inválido.", "danger")
            return render_template("register.html")

        password_hash = generate_password_hash(password)

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE email = %s LIMIT 1", (correo,))
                if cur.fetchone():
                    flash("El correo ya está registrado.", "warning")
                    return render_template("register.html")

                cur.execute(
                    "INSERT INTO users (name, email, phone, password_hash) VALUES (%s, %s, %s, %s)",
                    (nombre, correo, telefono, password_hash)
                )
                conn.commit()
            flash("Registro exitoso. Ya puedes iniciar sesión.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            conn.rollback()
            flash("Error al registrar usuario: " + str(e), "danger")
            return render_template("register.html")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form.get("correo", "").strip().lower()
        password = request.form.get("password", "")

        if not correo or not password:
            flash("Correo y contraseña son obligatorios.", "danger")
            return render_template("login.html")

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name, password_hash FROM users WHERE email = %s LIMIT 1", (correo,))
                row = cur.fetchone()
                if not row or not check_password_hash(row["password_hash"], password):
                    flash("Correo o contraseña incorrectos.", "danger")
                    return render_template("login.html")
                session["user_id"] = row["id"]
                session["user_name"] = row["name"]
                flash(f"Bienvenido, {row['name']}!", "success")
                return redirect(url_for("home"))
        finally:
            conn.close()
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
