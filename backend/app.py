from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector
from db_admin import create_user_db, create_mysql_user
from config import *
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "super-secret-key"

# Luu thong tin nguoi dung
def app_conn():
    return mysql.connector.connect(
        host = MYSQL_HOST,
        user = MYSQL_ADMIN_USER,
        password = MYSQL_ADMIN_PASS,
        database = 'user_db'
    )


def user_conn(username, password):
    return mysql.connector.connect(
        host = MYSQL_HOST,
        user = username,
        password = password
    )

@app.route("/")
def index():
    if "username" in session:
        return render_template("index.html", username=session["username"])
    return redirect("/login")

# REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = request.args.get("error")

    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        password_hash = generate_password_hash(password)

        if not username or not password:
            return render_template("register.html", error="Vui lòng nhập đầy đủ thông tin")

        try:
            # 1. Check the duplicate of username (user account)
            conn = app_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))

            if cursor.fetchone():
                cursor.close()
                conn.close()
                return render_template("register.html", error="Tên đăng nhập đã tồn tại!")

            # 2. Insert username data into user_db.
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, password_hash)
            )
            conn.commit()
            cursor.close()
            conn.close()

            # 3. Create user login and create db_username for user.
            create_mysql_user(username, password)
            create_user_db(username)

            return redirect(url_for('login', msg="username create login successful"))
        except Exception as e:
            return render_template("register.html", error=str(e))

    return render_template("register.html", error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = request.args.get("msg")
    error = request.args.get("error")

    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        try:
            # 1. Get the password hash from user_db
            conn = app_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()

            cursor.close()
            conn.close()

            if not result or not check_password_hash(result[0], password):
                return render_template('login.html', error='Wrong username or password')

            # 2. login to MySQL user
            try:
                mysql_conn = user_conn(username, password)
                mysql_conn.close()
            except:
                return render_template('login.html', error='database login failed')

            # 3. Successfully access
            session['username'] = username
            return redirect("/")

        except:
            return render_template('login.html', error='System errors')

    return render_template('login.html', notify=msg, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect("/login")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)