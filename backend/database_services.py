import re
from datetime import datetime
from flask import render_template, request, redirect, session, url_for, send_file
from werkzeug.utils import secure_filename
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


    # BACKUP DATABASE - BACKUP FULL
    @staticmethod
    def backup_database(bak_file_directory):
        if 'username' not in session:
            return redirect('/login')
        return None

    # RESTORE DATABASE
    @staticmethod
    def restore_database():
        '''
        Restore database từ file.dump hoặc .sql
        '''
        if 'username' not in session:
            return redirect('/login')

        dbname = request.form.get('dbname')
        if not dbname:
            return redirect(url_for('index', err_msg="Thiếu tên database"))

        username = session['username']
        user_pass = session['user_pass']

        # From Upload
        if 'file' not in request.files:
            return redirect(url_for('index', err_msg='Không có file upload!!'))

        file = request.files['file']
        if file.filename == '':
            return redirect(url_for('index', err_msg='Chưa chọn file!!'))

        # Kiểm tra extension file
        allowed_extensions = ('.dump', '.sql', '.bak', '.sql.gz')
        if not file.filename.lower().endswith(allowed_extensions):
            return redirect(url_for('index', err_msg=f'File phải có đuôi {", ".join(allowed_extensions)}!!'))

        tmp_path = None
        conn = None
        cursor = None

        try:
            # Tạo thư mục backup nếu chưa tồn tại
            if not os.path.exists(DEFAULT_BACKUP_DIR):
                os.makedirs(DEFAULT_BACKUP_DIR)

            # Lưu file tạm
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            original_filename = secure_filename(file.filename)
            tmp_path = os.path.join(DEFAULT_BACKUP_DIR, f'restore_{timestamp}_{original_filename}')
            file.save(tmp_path)

            # Xử lý file .sql.gz nếu cần
            if tmp_path.lower().endswith('.sql.gz'):
                import gzip
                decompressed_path = tmp_path[:-3]  # Bỏ .gz
                with gzip.open(tmp_path, 'rb') as f_in:
                    with open(decompressed_path, 'wb') as f_out:
                        f_out.write(f_in.read())
                os.remove(tmp_path)
                tmp_path = decompressed_path

            conn = mysql_admin.user_conn(username, user_pass)
            cursor = conn.cursor()

            # Tạo database mới nếu chưa tồn tại
            cursor.execute(f'''
                CREATE DATABASE IF NOT EXISTS `{dbname}` 
                    CHARACTER SET utf8mb4 
                    COLLATE utf8mb4_unicode_ci
            ''')

            # Chọn database để sử dụng
            cursor.execute(f'USE `{dbname}`;')

            # Đọc file SQL
            with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                sql_content = f.read()

            # Xử lý file lớn bằng cách đọc từng dòng
            buffer = ''
            lines_processed = 0
            statements_processed = 0

            for line in sql_content.splitlines():
                line = line.strip()

                # Bỏ qua comment và dòng trống
                if line.startswith('--') or line.startswith('/*') or line == '':
                    continue

                buffer += line + '\n'
                lines_processed += 1

                # Nếu có dấu chấm phẩy ở cuối dòng
                if ';' in line and not line.startswith('DELIMITER'):
                    try:
                        # Thực thi câu lệnh
                        cursor.execute(buffer)
                        statements_processed += 1

                        # Log tiến độ (tùy chọn)
                        if statements_processed % 100 == 0:
                            print(f"Đã xử lý {statements_processed} câu lệnh...")

                    except Exception as e:
                        # Log lỗi nhưng tiếp tục
                        print(f"Lỗi câu lệnh {statements_processed}: {str(e)[:100]}")
                        print(f"Câu lệnh: {buffer[:200]}...")

                    buffer = ''

            # Xử lý buffer còn lại (nếu có)
            if buffer.strip():
                try:
                    cursor.execute(buffer)
                    statements_processed += 1
                except Exception as e:
                    print(f"Lỗi câu lệnh cuối: {str(e)[:100]}")

            conn.commit()
            print(f"Restore hoàn tất! Đã xử lý {statements_processed} câu lệnh.")

            return redirect(url_for('index', msg=f"Restore database '{dbname}' thành công!"))

        except Exception as e:
            if conn:
                conn.rollback()
            error_msg = f"LỖI RESTORE DATABASE: {str(e)}"
            print(error_msg)
            return redirect(url_for('index', err_msg=error_msg))

        finally:
            # Đảm bảo đóng kết nối và xóa file tạm
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass
