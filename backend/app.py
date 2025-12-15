from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector
from db_admin import create_user_db, create_mysql_user, admin_conn
from config import *
import re

app = Flask(__name__)
app.secret_key = "super-secret-key"

# LƯU THÔNG TIN CỦA NGƯỜI DÙNG VÀO user_db
def app_conn():
    return mysql.connector.connect(
        host = MYSQL_HOST,
        user = MYSQL_ADMIN_USER,
        password = MYSQL_ADMIN_PASS,
        database = 'user_db'
    )

# KẾT NỐI TỚI LOGIN CỦA user
def user_conn(username, password):
    return mysql.connector.connect(
        host = MYSQL_HOST,
        user = username,
        password = password
    )


# TRANG CHỦ
@app.route("/")
def index():
    if "username" in session:
        username = session['username']
        user_pass = session['user_pass']

        # Lấy danh sách databases từ MySQL
        mysql_conn = user_conn(username, user_pass)
        cur = mysql_conn.cursor()
        cur.execute("SHOW DATABASES")

        dbs = [
            row[0] for row in cur.fetchall()
            if row[0] not in ("information_schema", "mysql", "sys", "performance_schema")
        ]

        mysql_conn.close()
        return render_template("databases.html", database=dbs, username=username)  # <-- THÊM database=dbs

    return redirect("/login")

# ĐĂNG KÝ TÀI KHOẢN
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = request.args.get("error")

    if request.method == "POST":
        # LẤY username và password. Băm (mã hóa) password
        username = request.form['username']
        password = request.form['password']

        # CHỈ CHO PHÉP TÀI KHOẢN KHÔNG CHỨA KÝ TỰ ĐẶC BIỆT HAY KHOẢNG TRẮNG
        if not re.match(r"^[a-zA-Z0-9_-]+$", username):
            return render_template("register.html", error='Username không được chứa ký tự đặc biệt hay khoảng trắng')

        # NHẬP KHÔNG ĐỦ THÔNG TIN
        if not username or not password:
            return render_template("register.html", error="Vui lòng nhập đầy đủ thông tin")

        try:
            # 1. KIỂM TRA TÀI KHOẢN BỊ TRÙNG (ĐÃ TỒN TẠI) - NẾU ĐÃ TỒN TẠI username -> BÁO LỖI
            conn = app_conn()
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

            # 3. TẠO LOGIN CHO user VÀ TẠO DATABASE DEFAULT CHO user
            create_mysql_user(username, password)
            create_user_db(username, username)

            return redirect(url_for('login', msg="username create login successful"))
        except Exception as e:
            return render_template("register.html", error=str(e))

    return render_template("register.html", error=error)

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = request.args.get("msg")
    error = request.args.get("error")

    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        try:
            # 1. LẤY PASSWORD
            conn = app_conn()
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
                mysql_conn = user_conn(username, password)
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

# LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect("/login")

# SHOW DATABASES

@app.route('/database/<dbname>')
def list_tables(dbname):
    if 'username' not in session:
        return redirect("/login")
    username = session['username']
    password = session['user_pass']
    conn = user_conn(username, password)
    cursor = conn.cursor()
    cursor.execute(f'SHOW TABLES FROM `{dbname}`;')
    tables = [t[0] for t in cursor.fetchall()]
    conn.close()

    return render_template('tables.html', dbname=dbname, tables=tables)


# SELECT
@app.route('/database/<dbname>/<table>')
def view_table(dbname, table):
    conn = user_conn(session['username'], session['user_pass'])
    cursor = conn.cursor()

    cursor.execute(f'DESCRIBE `{dbname}`.`{table}`;')
    columns = cursor.fetchall()

    cursor.execute(f'SELECT * FROM `{dbname}`.`{table}`;')
    rows = cursor.fetchall()

    conn.close()

    return render_template('table_view.html', dbname=dbname, table=table, columns=columns, rows=rows)

# ADD COLUMN
@app.route('/database/<dbname>/<table>/add_column', methods=['POST'])
def add_column(dbname, table):
    col = request.form.get('column')
    dtype = request.form.get('dtype', 'varchar')

    if col.lower() == 'id':
        return 'CANNOT FORMAT id COLUMN'

    type_map = {
        "varchar": "VARCHAR(255)",
    }

    conn = user_conn(session['username'], session['user_pass'])
    cursor = conn.cursor()
    cursor.execute(f'ALTER TABLE `{dbname}`.`{table}` ADD COLUMN `{col}` {type_map[dtype]};')
    conn.commit()
    conn.close()

    return redirect(f'/database/{dbname}/{table}')

# DROP COLUMN
@app.route('/database/<dbname>/<table>/drop_column', methods=['POST'])
def drop_column(dbname, table):
    col = request.form['column']

    if col == "id":
        return "KHÔNG ĐƯỢC XÓA ID"

    conn = user_conn(session['username'], session['user_pass'])
    cursor = conn.cursor()
    cursor.execute(f'ALTER TABLE `{dbname}`.`{table}` DROP COLUMN `{col}`;')
    conn.commit()
    conn.close()

    return redirect(f'/database/{dbname}/{table}')

# RENAME COLUMN
@app.route('/database/<dbname>/<table>/rename_column', methods=['POST'])
def rename_column(dbname, table):
    old_col = request.form['old_column']
    new_col = request.form['new_column']

    if old_col == 'id':
        return 'KHÔNG ĐƯỢC ĐỔI TÊN CỘT id'

    if not re.match(r"^[a-zA-Z0-9_]+$", new_col):
        return "Tên cột mới không hợp lệ!"

    conn = user_conn(session['username'], session['user_pass'])
    cursor = conn.cursor()

    cursor.execute(f"SHOW COLUMNS FROM `{dbname}`.`{table}` LIKE %s;", (old_col,))
    col_info = cursor.fetchone()

    if not col_info:
        return "Cột không tồn tại!"

    sql = f"""
      ALTER TABLE `{dbname}`.`{table}`
      CHANGE `{old_col}` `{new_col}` VARCHAR(255);
      """
    cursor.execute(sql)
    conn.commit()
    conn.close()

    return redirect(f'/database/{dbname}/{table}')

# ADD ROW
@app.route('/database/<dbname>/<table>/add_row', methods=['POST'])
def add_row(dbname, table):
    conn = user_conn(session['username'], session['user_pass'])
    cursor = conn.cursor()

    cursor.execute(f'DESCRIBE `{dbname}`.`{table}`;')
    columns = [col[0] for col in cursor.fetchall()]

    values = []
    for col in columns:
        values.append(request.form.get(col))

    cols_str = ','.join(f'`{c}`' for c in columns)
    placeholders = ','.join(['%s'] * len(values))
    try:
        cursor.execute(f"INSERT INTO `{dbname}`.`{table}` ({cols_str}) VALUES ({placeholders})", values)
        conn.commit()
        conn.close()
    except Exception as e:
        conn.rollback()
        return redirect(url_for('view_table', dbname=dbname, table=table, err_msg=str(e)))

    return redirect(f'/database/{dbname}/{table}')

# EDIT ROW
@app.route('/database/<dbname>/<table>/edit_row/<rowid>', methods=['POST'])
def edit_row(dbname, table, rowid):
    conn = user_conn(session['username'], session['user_pass'])
    cursor = conn.cursor()

    cursor.execute(f"DESCRIBE `{dbname}`.`{table}`;")
    columns = [col[0] for col in cursor.fetchall()]

    assignments = []
    values = []

    for col in columns:
        assignments.append(f'`{col}`=%s')
        values.append(request.form.get(col))

    values.append(rowid)

    sql = f"UPDATE `{dbname}`.`{table}` SET {','.join(assignments)} WHERE id=%s"
    cursor.execute(sql, values)
    conn.commit()
    conn.close()

    return redirect(f'/database/{dbname}/{table}')

# DELETE ROW
@app.route('/database/<dbname>/<table>/delete_row/<rowid>')
def delete_row(dbname, table, rowid):
    conn = user_conn(session['username'], session['user_pass'])
    cursor = conn.cursor()

    cursor.execute(f'DELETE FROM `{dbname}`.`{table}` WHERE id=%s', (rowid,))
    conn.commit()
    conn.close()

    return redirect(f'/database/{dbname}/{table}')

# TAO DATABASE
@app.route('/create_database', methods=['POST'])
def create_database():
    if 'username' not in session:
        return redirect('/login')

    dbname = request.form['dbname']

    if not re.match(r"^[a-zA-Z0-9_]+$", dbname):
        return "Tên database không hợp lệ"

    db_name = request.form.get('dbname')
    username = session["username"]

    try:
        create_user_db(username, db_name)
        return redirect(url_for('index', msg="TẠO DATABASE THÀNH CÔNG"))

    except Exception as e:
        return f"Lỗi khi tạo database: {e}"


# XOA DATABASE
@app.route('/drop_database/<dbname>')
def drop_database(dbname):
    if 'username' not in session:
        return redirect('/login')

    try:
        conn = admin_conn()
        cursor = conn.cursor()
        cursor.execute(f"DROP DATABASE `{dbname}`;")
        cursor.execute("FLUSH PRIVILEGES;")

        conn.commit()
        conn.close()
        return redirect(url_for('index', msg="XÓA DATABASE THÀNH CÔNG"))

    except Exception as e:
        return f"Lỗi khi xóa database: {e}"

# TAO TABLE
@app.route('/database/<dbname>/create_table', methods=['POST'])
def create_table(dbname):
    if 'username' not in session:
        return redirect('/login')

    table = request.form['table_name']
    if not re.match(r"^[a-zA-Z0-9_]+$", table):
        return "Tên bảng không hợp lệ"

    conn = user_conn(session['username'], session['user_pass'])
    cursor = conn.cursor()

    sql = f"""
    CREATE TABLE `{dbname}`.`{table}` (
        id INT
    );
    """

    try:
        cursor.execute(sql)
        conn.commit()

    except Exception as e:
        return str(e)


    conn.close()
    return redirect(url_for('list_tables',  dbname=dbname, msg="Thêm bảng thành công!!!"))

# DROP TABLE
@app.route('/database/<dbname>/drop_table/<table>')
def drop_table(dbname, table):
    if "username" not in session:
        return redirect("/login")

    conn = user_conn(session['username'], session['user_pass'])
    cursor = conn.cursor()

    try:
        cursor.execute(f"DROP TABLE `{dbname}`.`{table}`;")
        conn.commit()
    except Exception as e:
        return str(e)

    conn.close()
    return redirect(url_for('list_tables',  dbname=dbname, msg="Xóa bảng thành công!!!"))


# ADD PRIMARY KEY
@app.route('/database/<dbname>/<table>/add_primary_key', methods=['POST'])
def add_primary_key(dbname, table):
    # Lấy list các cột
    columns = request.form.getlist("columns")

    if not columns:
        return redirect(f"/database/{dbname}/{table}?err_msg=Chưa chọn cột")

    conn = user_conn(session['username'], session['user_pass'])
    cursor = conn.cursor()

    # 1. Check Primary Key
    cursor.execute("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND CONSTRAINT_NAME = 'PRIMARY'
    """, (dbname, table))

    if cursor.fetchone():
        conn.close()
        return redirect(f"/database/{dbname}/{table}?err_msg=Đã có PRIMARY KEY!!!")

    # 2. MODIFY columns -> not null
    for col in columns:
        cursor.execute(f"ALTER TABLE {dbname}.{table} MODIFY `{col}` NVARCHAR(255) NOT NULL")

    try:
        # 3. ADD COMPOSITE PK
        cols = ', '.join(f"`{c}`" for c in columns)
        cursor.execute(f"ALTER TABLE {dbname}.{table} ADD PRIMARY KEY ({cols})")
        conn.commit()
        conn.close()
    except Exception as e:
        conn.rollback()
        return redirect(url_for('view_table', dbname=dbname, table=table, msg=str(e)))

    return redirect(f"/database/{dbname}/{table}?msg=Thêm PRIMARY KEY thành công!!!!")

# DROP PRIMARY KEY

@app.route('/database/<dbname>/<table>/drop_primary_key', methods=['POST'])
def drop_primary_key(dbname, table):
    conn = user_conn(session['username'], session['user_pass'])
    cursor = conn.cursor()

    # 1. Check PK
    cursor.execute("""
            SELECT 1
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND CONSTRAINT_NAME = 'PRIMARY'
            LIMIT 1
        """, (dbname, table))

    if not cursor.fetchone():
        conn.close()
        return redirect(f"/database/{dbname}/{table}?err_msg=CHƯA CÓ PRIMARY KEY!!")

    try:
        # 2. Xóa PK
        cursor.execute(f"ALTER TABLE {dbname}.{table} DROP PRIMARY KEY")
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return redirect(url_for('view_table', dbname=dbname, table=table, msg=str(e)))
    conn.close()
    return redirect(f"/database/{dbname}/{table}?msg=XÓA PRIMARY KEY THÀNH CÔNG")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)