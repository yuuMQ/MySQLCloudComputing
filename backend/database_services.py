import re
from flask import render_template, request, redirect, session, url_for
from db_admin import MySQLAdmin
import os


mysql_admin = MySQLAdmin()

DEFAULT_BACKUP_DIR = 'backups'
os.makedirs(DEFAULT_BACKUP_DIR, exist_ok=True)

class DatabaseServices:
    # SHOW DATABASES
    @staticmethod
    def show_databases():
        if "username" in session:
            username = session['username']
            user_pass = session['user_pass']

            # Lấy danh sách databases từ MySQL
            mysql_conn = mysql_admin.user_conn(username, user_pass)
            cur = mysql_conn.cursor()
            cur.execute("SHOW DATABASES")

            dbs = [
                row[0] for row in cur.fetchall()
                if row[0] not in ("information_schema", "mysql", "sys", "performance_schema")
            ]

            mysql_conn.close()
            return render_template("databases.html", database=dbs, username=username)  # <-- THÊM database=dbs

        return redirect("/login")

    # CREATE DATABASE
    @staticmethod
    def create_database():
        if 'username' not in session:
            return redirect('/login')

        dbname = request.form['dbname']

        if not re.match(r"^[a-zA-Z0-9_]+$", dbname):
            return "Tên database không hợp lệ"

        db_name = request.form.get('dbname')
        username = session["username"]

        try:
            mysql_admin.create_user_db(username, db_name)
            return redirect(url_for('index', msg="TẠO DATABASE THÀNH CÔNG"))

        except Exception as e:
            return f"Lỗi khi tạo database: {e}"

    # DROP DATABASE
    @staticmethod
    def drop_database(dbname):
        if 'username' not in session:
            return redirect('/login')

        try:
            conn = mysql_admin.admin_conn()
            cursor = conn.cursor()
            cursor.execute(f"DROP DATABASE `{dbname}`;")
            cursor.execute("FLUSH PRIVILEGES;")

            conn.commit()
            conn.close()
            return redirect(url_for('index', msg="XÓA DATABASE THÀNH CÔNG"))

        except Exception as e:
            return f"Lỗi khi xóa database: {e}"
