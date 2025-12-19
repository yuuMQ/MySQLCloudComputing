from flask import render_template, request, redirect, session, url_for
from db_admin import MySQLAdmin

mysql_admin = MySQLAdmin()

class KeyServices:
    # ADD PRIMARY KEY
    @staticmethod
    def add_primary_key(dbname, table):
        # Lấy list các cột
        columns = request.form.getlist("columns")

        if not columns:
            return redirect(f"/database/{dbname}/{table}?err_msg=Chưa chọn cột")

        conn = mysql_admin.user_conn(session['username'], session['user_pass'])
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


    @staticmethod
    def drop_primary_key(dbname, table):
        conn = mysql_admin.user_conn(session['username'], session['user_pass'])
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
