import os
import re
import pymysql
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import random
import redis
import json
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambia_esto_en_produccion")

# DB config desde variables de entorno
DB_HOST = os.environ.get("MYSQL_HOST", "mysql")
DB_USER = os.environ.get("MYSQL_USER", "appuser")
DB_PASSWORD = os.environ.get("MYSQL_PASSWORD", "apppassword")
DB_NAME = os.environ.get("MYSQL_DATABASE", "appdb")
DB_PORT = int(os.environ.get("MYSQL_PORT", 3306))


# Configuración Redis
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))


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

def get_redis_connection():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

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


# CASO 1: Caché de usuarios frecuentes
def get_user_with_cache(user_id):
    r = get_redis_connection()
    cache_key = f"user:{user_id}"
    
    # Intentar obtener del caché
    cached_user = r.get(cache_key)
    if cached_user:
        return json.loads(cached_user)
    
    # Si no está en caché, buscar en MySQL
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            
            # Guardar en caché por 5 minutos
            if user:
                r.setex(cache_key, 300, json.dumps(user, default=str))
            return user
    finally:
        conn.close()

# CASO 2: Sesiones en Redis (mejor que cookies)
def redis_session(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = request.cookies.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
        
        r = get_redis_connection()
        session_data = r.get(f"session:{session_id}")
        
        if session_data:
            request.session = json.loads(session_data)
        else:
            request.session = {}
        
        response = f(*args, **kwargs)
        
        # Guardar sesión actualizada
        r.setex(f"session:{session_id}", 3600, json.dumps(request.session))
        response.set_cookie('session_id', session_id, max_age=3600)
        
        return response
    return decorated_function

# CASO 3: Contador de registros en tiempo real
def increment_registration_counter():
    r = get_redis_connection()
    r.incr("total_registrations")
    return r.get("total_registrations")

# En tu ruta de registro
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # ... lógica existente de MySQL ...
        
        # Incrementar contador en Redis
        total_regs = increment_registration_counter()
        logger.info(f"Registro #{total_regs} completado")
        
        # Cachear el nuevo usuario
        r = get_redis_connection()
        r.setex(f"user:{user_id}", 300, json.dumps({
            "id": user_id,
            "name": nombre,
            "email": correo
        }))


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
