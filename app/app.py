import os
import re
import pymysql
import uuid
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from werkzeug.security import generate_password_hash, check_password_hash
import random
import redis
import json
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambia_esto_en_produccion")

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DB config desde variables de entorno
DB_HOST = os.environ.get("MYSQL_HOST", "mysql")
DB_USER = os.environ.get("MYSQL_USER", "appuser")
DB_PASSWORD = os.environ.get("MYSQL_PASSWORD", "apppassword")
DB_NAME = os.environ.get("MYSQL_DATABASE", "appdb")
DB_PORT = int(os.environ.get("MYSQL_PORT", 3306))

# Configuración Redis
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

# Pool de conexiones Redis
redis_pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

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
    return redis.Redis(connection_pool=redis_pool)

def valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def login_required(fn):
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
        logger.info(f"Usuario {user_id} obtenido desde caché Redis")
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
                logger.info(f"Usuario {user_id} guardado en caché Redis")
            return user
    finally:
        conn.close()

# CASO 2: Sesiones en Redis (CORREGIDO)
def redis_session(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = request.cookies.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())

        r = get_redis_connection()
        session_data = r.get(f"session:{session_id}")

        if session_data:
            try:
                session.update(json.loads(session_data))
            except json.JSONDecodeError:
                logger.warning("Sesión corrupta en Redis, creando nueva")
                session.clear()

        # Ejecutar la vista y obtener respuesta
        view_response = f(*args, **kwargs)
        
        # Guardar sesión actualizada en Redis
        r.setex(f"session:{session_id}", 3600, json.dumps(dict(session)))
        
        # Convertir a objeto Response si es necesario
        if isinstance(view_response, str):
            response = make_response(view_response)
        elif hasattr(view_response, 'set_cookie'):
            response = view_response
        else:
            response = make_response(view_response)
            
        response.set_cookie('session_id', session_id, max_age=3600, httponly=True)
        return response
    return decorated_function

# CASO 3: Contador de registros en tiempo real
def increment_registration_counter():
    r = get_redis_connection()
    total_regs = r.incr("total_registrations")
    logger.info(f"Contador de registros incrementado: {total_regs}")
    return total_regs

# CASO 4: Guardar último login en Redis
def set_last_login(user_id, user_name):
    r = get_redis_connection()
    login_key = f"last_login:{user_id}"
    r.setex(login_key, 86400, user_name)  # Expira en 24 horas
    logger.info(f"Último login guardado para usuario {user_id}")

@app.route("/")
@login_required
@redis_session
def home():
    value = random.randint(0, 100)
    user_name = session.get("user_name")

    # Usar caché para obtener datos del usuario
    user_id = session.get("user_id")
    user_data = get_user_with_cache(user_id) if user_id else None

    # Guardar último acceso en Redis
    if user_id:
        r = get_redis_connection()
        r.setex(f"last_access:{user_id}", 300, "active")  # 5 minutos

    return render_template("index.html", random_value=value, user_name=user_name, user_data=user_data)

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
                user_id = cur.lastrowid
                conn.commit()

                # INCREMENTAR CONTADOR EN REDIS
                total_regs = increment_registration_counter()

                # GUARDAR USUARIO EN CACHÉ REDIS
                r = get_redis_connection()
                user_data = {
                    "id": user_id,
                    "name": nombre,
                    "email": correo,
                    "phone": telefono
                }
                r.setex(f"user:{user_id}", 300, json.dumps(user_data))

                flash(f"Registro exitoso. Eres el usuario #{total_regs}. Ya puedes iniciar sesión.", "success")
                return redirect(url_for("login"))
        except Exception as e:
            conn.rollback()
            logger.error(f"Error en registro: {str(e)}")
            flash("Error al registrar usuario.", "danger")
            return render_template("register.html")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
@redis_session
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

                # INCREMENTAR CONTADOR DE LOGINS EN REDIS
                r = get_redis_connection()
                r.incr("total_logins")

                # GUARDAR ÚLTIMO LOGIN EN REDIS
                set_last_login(row["id"], row["name"])

                flash(f"Bienvenido, {row['name']}!", "success")
                return redirect(url_for("home"))
        except Exception as e:
            logger.error(f"Error en login: {str(e)}")
            flash("Error al iniciar sesión.", "danger")
            return render_template("login.html")
        finally:
            conn.close()
    return render_template("login.html")

@app.route("/logout")
@redis_session
def logout():
    user_id = session.get("user_id")
    if user_id:
        # Limpiar datos de Redis
        r = get_redis_connection()
        r.delete(f"last_access:{user_id}")
        # También limpiar la sesión de Redis
        session_id = request.cookies.get('session_id')
        if session_id:
            r.delete(f"session:{session_id}")

    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("login"))

@app.route("/stats")
@login_required
@redis_session
def stats():
    r = get_redis_connection()
    total_registrations = r.get("total_registrations") or "0"
    total_logins = r.get("total_logins") or "0"
    
    # Obtener todas las claves de sesión activas
    session_keys = r.keys("session:*")
    active_sessions = len(session_keys)

    return render_template("stats.html",
                         total_registrations=total_registrations,
                         total_logins=total_logins,
                         active_sessions=active_sessions)

@app.route("/redis-test")
@login_required
@redis_session
def redis_test():
    """Página para probar funcionalidades de Redis"""
    r = get_redis_connection()
    
    # Probar diferentes operaciones Redis
    test_data = {
        "total_registrations": r.get("total_registrations") or "0",
        "total_logins": r.get("total_logins") or "0",
        "active_sessions": len(r.keys("session:*")),
        "cached_users": len(r.keys("user:*")),
        "last_access_keys": len(r.keys("last_access:*")),
        "last_login_keys": len(r.keys("last_login:*")),
        "redis_info": r.info("memory")
    }
    
    return render_template("redis_test.html", test_data=test_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
