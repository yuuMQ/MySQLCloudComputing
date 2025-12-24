from flask import jsonify, render_template, request, redirect, session, url_for
from db_admin import MySQLAdmin
import re
from key_services import KeyServices
from mysql.connector import IntegrityError
mysql_admin = MySQLAdmin()

class TableServices:
    # Show Tables
    @staticmethod
    def list_tables(dbname):
        if 'username' not in session:
            return redirect("/login")
        username = session['username']
        password = session['user_pass']
        conn = mysql_admin.user_conn(username, password)
        cursor = conn.cursor()
        cursor.execute(f'SHOW TABLES FROM `{dbname}`;')
        tables = [t[0] for t in cursor.fetchall()]
        conn.close()

        return render_template('tables.html', dbname=dbname, tables=tables)

    # SELECT
    @staticmethod
    def view_table(dbname, table):
        conn = mysql_admin.user_conn(session['username'], session['user_pass'])
        cursor = conn.cursor()

        cursor.execute(f'DESCRIBE `{dbname}`.`{table}`;')
        columns = cursor.fetchall()

        cursor.execute(f'SELECT * FROM `{dbname}`.`{table}`;')
        rows = cursor.fetchall()

        # FK
        cursor.execute("""
                SELECT CONSTRAINT_NAME, COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s
                    AND TABLE_NAME = %s
                    AND REFERENCED_TABLE_NAME IS NOT NULL
                """, (dbname, table))
        foreign_keys = cursor.fetchall()

        # REFERENCE TABLE
        cursor.execute("""
                SELECT
                    TABLE_NAME,
                    COLUMN_NAME,
                    CONSTRAINT_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s
                    AND REFERENCED_TABLE_NAME = %s
                """, (dbname, table))
        referenced_by = cursor.fetchall()
        cursor.execute("SHOW TABLES FROM `{}`;".format(dbname))
        tables = [t[0] for t in cursor.fetchall()]
        conn.close()

        return render_template('table_view.html', dbname=dbname, table=table, columns=columns, rows=rows, tables=tables, foreign_keys=foreign_keys, referenced_by=referenced_by)


    # Create Table
    @staticmethod
    def create_table(dbname):
        if 'username' not in session:
            return redirect('/login')

        table = request.form['table_name']
        if not re.match(r"^[a-zA-Z0-9_]+$", table):
            return "Tên bảng không hợp lệ"

        conn = mysql_admin.user_conn(session['username'], session['user_pass'])
        cursor = conn.cursor()

        sql = f"""
        CREATE TABLE `{dbname}`.`{table}` (
            id VARCHAR(255) PRIMARY KEY NOT NULL
        );
        """

        try:
            cursor.execute(sql)
            conn.commit()

        except Exception as e:
            return str(e)

        conn.close()
        return redirect(url_for('list_tables', dbname=dbname, msg="Thêm bảng thành công!!!"))

    # Drop Table
    @staticmethod
    def drop_table(dbname, table):
        if "username" not in session:
            return redirect("/login")

        conn = mysql_admin.user_conn(session['username'], session['user_pass'])
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s
                    AND REFERENCED_TABLE_NAME = %s
            """, (dbname, table))
            refs = cursor.fetchall()
            if refs:
                conn.close()
                return redirect(url_for("list_tables", dbname=dbname, msg=f"Không thể xóa. Đang được tham chiếu bởi: {[r[0] for r in refs]}"))
            else:
                cursor.execute(f"DROP TABLE `{dbname}`.`{table}`;")
                conn.commit()

        except Exception as e:
            return str(e)

        conn.close()
        return redirect(url_for('list_tables', dbname=dbname, msg="Xóa bảng thành công!!!"))

    # -------------- COLUMN --------------------

    # GET COLUMNS
    @staticmethod
    def get_table_columns(dbname, table):
        if "username" not in session:
            return jsonify(columns=[]), 401

        try:
            conn = mysql_admin.user_conn(session['username'], session['user_pass'])
            cursor = conn.cursor()

            # Lấy danh sách các cột
            cursor.execute(f"DESCRIBE `{dbname}`.`{table}`;")
            cols = [c[0] for c in cursor.fetchall()]

            conn.close()
            return jsonify(columns=cols)
        except Exception as e:
            return jsonify(columns=[], error=str(e)), 500

    # Add Column
    @staticmethod
    def add_column(dbname, table):
        col = request.form.get('column')
        dtype = request.form.get('dtype', 'varchar')

        type_map = {
            "varchar": "VARCHAR(255)",
        }

        conn = mysql_admin.user_conn(session['username'], session['user_pass'])
        cursor = conn.cursor()
        cursor.execute(f'ALTER TABLE `{dbname}`.`{table}` ADD COLUMN `{col}` {type_map[dtype]};')
        conn.commit()
        conn.close()

        return redirect(f'/database/{dbname}/{table}')

    # Drop Column
    @staticmethod
    def drop_column(dbname, table):
        col = request.form['column']

        conn = mysql_admin.user_conn(session['username'], session['user_pass'])
        cursor = conn.cursor()

        try:
            cursor.execute("""
                        SELECT CONSTRAINT_NAME
                        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                        WHERE TABLE_SCHEMA = %s
                          AND TABLE_NAME = %s
                          AND COLUMN_NAME = %s
                          AND REFERENCED_TABLE_NAME IS NOT NULL
             """, (dbname, table, col))
            fk = cursor.fetchone()
            if fk:
                cursor.execute(
                    f"ALTER TABLE `{dbname}`.`{table}` DROP FOREIGN KEY `{fk[0]}`"
                )

            cursor.execute("""
                SELECT 1
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s
                    AND REFERENCED_TABLE_NAME = %s
                    AND REFERENCED_COLUMN_NAME = %s
            """, (dbname, table, col))
            if cursor.fetchone():
                conn.close()
                return redirect(f"/database/{dbname}/{table}?err_msg=Cột đang được bảng khác tham chiếu")

            cursor.execute('''
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s
                    AND TABLE_NAME = %s
            ''', (dbname, table))
            col_count = cursor.fetchone()[0]
            if col_count <= 1:
                conn.close()
                return redirect(f"/database/{dbname}/{table}?err_msg=Không thể xóa cột cuối cùng!!")

            cursor.execute(f'ALTER TABLE `{dbname}`.`{table}` DROP COLUMN `{col}`;')
            conn.commit()

        except Exception as e:
            conn.rollback()
            conn.close()
            return redirect(
                f"/database/{dbname}/{table}?err_msg={str(e)}"
            )

        conn.close()
        return redirect(f'/database/{dbname}/{table}')

    # Rename Column
    @staticmethod
    def rename_column(dbname, table):
        old_col = request.form['old_column']
        new_col = request.form['new_column']

        if not re.match(r"^[a-zA-Z0-9_]+$", new_col):
            return "Tên cột mới không hợp lệ!"

        conn = mysql_admin.user_conn(session['username'], session['user_pass'])
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

    # ------------------- ROW ------------------

    # Add Row
    @staticmethod
    def add_row(dbname, table):
        conn = mysql_admin.user_conn(session['username'], session['user_pass'])
        cursor = conn.cursor()

        pk = KeyServices.get_primary_key(cursor, dbname, table)
        pk_value = request.form.get(pk)

        cursor.execute(f'DESCRIBE `{dbname}`.`{table}`;')
        columns = [col[0] for col in cursor.fetchall()]

        if pk_value is None or pk_value.strip() == "":
            return redirect(
                f"/database/{dbname}/{table}?err_msg=PRIMARY KEY không được rỗng"
            )

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

    # Edit Row
    @staticmethod
    def edit_row(dbname, table, rowid):
        conn = mysql_admin.user_conn(session['username'], session['user_pass'])
        cursor = conn.cursor()

        pk = KeyServices.get_primary_key(cursor, dbname, table)
        if not pk:
            conn.close()
            return redirect(f"/database/{dbname}/{table}?err_msg=Bảng chưa có PRIMARY KEY nên không thể sửa dòng")
        cursor.execute(f"DESCRIBE `{dbname}`.`{table}`;")
        columns = [col[0] for col in cursor.fetchall()]

        assignments = []
        values = []

        for col in columns:
            assignments.append(f'`{col}`=%s')
            values.append(request.form.get(col))

        values.append(rowid)

        sql = f"UPDATE `{dbname}`.`{table}` SET {','.join(assignments)} WHERE `{pk}`=%s"
        try:
            cursor.execute(sql, values)
            conn.commit()
            conn.close()
            return redirect(f"/database/{dbname}/{table}?msg=Cập nhật thành công")
        except Exception as e:
            conn.rollback()
            conn.close()
            return redirect(f'/database/{dbname}/{table}?err_msg={str(e)}')

    # Delete Row
    @staticmethod
    def delete_row(dbname, table, rowid):
        conn = mysql_admin.user_conn(session['username'], session['user_pass'])
        cursor = conn.cursor()

        pk = KeyServices.get_primary_key(cursor, dbname, table)

        cursor.execute(f'DELETE FROM `{dbname}`.`{table}` WHERE `{pk}`=%s', (rowid,))
        conn.commit()
        conn.close()

        return redirect(f'/database/{dbname}/{table}')