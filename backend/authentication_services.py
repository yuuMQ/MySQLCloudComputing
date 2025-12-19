import re
from flask import render_template, request, redirect, session, url_for
from db_admin import MySQLAdmin

mysql_admin = MySQLAdmin()

# Register And Login
class AuthServices:
    @staticmethod
    def register():
        error = request.args.get("error")

        if request.method == "POST":
            # LẤY username và password. Băm (mã hóa) password
            username = request.form['username']
            password = request.form['password']

            # CHỈ CHO PHÉP TÀI KHOẢN KHÔNG CHỨA KÝ TỰ ĐẶC BIỆT HAY KHOẢNG TRẮNG
            if not re.match(r"^[a-zA-Z0-9_-]+$", username):
                return render_template("register.html",
                                       error='Username không được chứa ký tự đặc biệt hay khoảng trắng')

            # NHẬP KHÔNG ĐỦ THÔNG TIN
            if not username or not password:
                return render_template("register.html", error="Vui lòng nhập đầy đủ thông tin")

            try:
                # 1. KIỂM TRA TÀI KHOẢN BỊ TRÙNG (ĐÃ TỒN TẠI) - NẾU ĐÃ TỒN TẠI username -> BÁO LỖI
                conn = mysql_admin.app_conn()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))

                if cursor.fetchone():
                    cursor.close()
                    conn.close()
                    return render_template("register.html", error="Tên đăng nhập đã tồn tại!")

                # 2. INSERT username VÀO BẢNG users TRONG user_db do admin quản lý
                cursor.execute(
                    "INSERT INTO users (username, password) VALUES (%s, %s)",
                    (username, password)
                )
                conn.commit()
                cursor.close()
                conn.close()

                # 3. TẠO LOGIN CHO user VÀ TẠO DATABASE DEFAULT CHO user (Được thực hiện bằng admin account)
                mysql_admin.create_mysql_user(username, password)
                mysql_admin.create_user_db(username, username)

                return redirect(url_for('login', msg="username create login successful"))
            except Exception as e:
                return render_template("register.html", error=str(e))

        return render_template("register.html", error=error)

    @staticmethod
    def login():
        msg = request.args.get("msg")
        error = request.args.get("error")

        if request.method == "POST":
            username = request.form['username']
            password = request.form['password']

            try:
                # 1. LẤY PASSWORD
                conn = mysql_admin.app_conn()
                cursor = conn.cursor()
                cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
                result = cursor.fetchone()

                cursor.close()
                conn.close()

                # THÔNG TIN SAI -> BÁO LỖI
                if not result or result[0] != password:
                    return render_template('login.html', error='Wrong username or password')

                # 2. ĐĂNG NHẬP VÀO mysql
                try:
                    mysql_conn = mysql_admin.user_conn(username, password)
                    mysql_conn.close()
                except:
                    return render_template('login.html', error='database login failed')

                # 3. ĐĂNG NHẬP THÀNH CÔNG
                session['username'] = username
                session['user_pass'] = password
                session['db_name'] = f"db_{username}"
                return redirect("/")

            except:
                return render_template('login.html', error='System errors')

        return render_template('login.html', notify=msg, error=error)

    @staticmethod
    def logout():
        session.clear()
        return redirect("/login")
