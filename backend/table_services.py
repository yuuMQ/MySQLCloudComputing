from flask import render_template, request, redirect, session, url_for
from db_admin import MySQLAdmin
import re

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

        conn.close()

        return render_template('table_view.html', dbname=dbname, table=table, columns=columns, rows=rows)


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
            id NVARCHAR(255) PRIMARY KEY
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
            cursor.execute(f"DROP TABLE `{dbname}`.`{table}`;")
            conn.commit()
        except Exception as e:
            return str(e)

        conn.close()
        return redirect(url_for('list_tables', dbname=dbname, msg="Xóa bảng thành công!!!"))

    # -------------- COLUMN --------------------

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
                        SELECT 1
                        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                        WHERE TABLE_SCHEMA = %s
                          AND TABLE_NAME = %s
                          AND COLUMN_NAME = %s
                          AND CONSTRAINT_NAME = 'PRIMARY'
                    """, (dbname, table, col))

            is_pk = cursor.fetchone()
            if is_pk:
                cursor.execute(f"ALTER TABLE `{dbname}`.`{table}` DROP PRIMARY KEY")

            cursor.execute(f'ALTER TABLE `{dbname}`.`{table}` DROP COLUMN `{col}`;')
            conn.commit()

        except Exception as e:
            conn.rollback()
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

    # Edit Row
    @staticmethod
    def edit_row(dbname, table, rowid):
        conn = mysql_admin.user_conn(session['username'], session['user_pass'])
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

    # Delete Row
    @staticmethod
    def delete_row(dbname, table, rowid):
        conn = mysql_admin.user_conn(session['username'], session['user_pass'])
        cursor = conn.cursor()

        cursor.execute(f'DELETE FROM `{dbname}`.`{table}` WHERE id=%s', (rowid,))
        conn.commit()
        conn.close()

        return redirect(f'/database/{dbname}/{table}')