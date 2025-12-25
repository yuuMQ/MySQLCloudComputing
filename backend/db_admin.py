'''
    - Nhan du lieu -> tao user va cap quyen db_user cho user.
'''
import mysql.connector
from config import *

class MySQLAdmin:
    def __init__(self):
        self.host = MYSQL_HOST
        self.admin_user = MYSQL_ADMIN_USER
        self.admin_pass = MYSQL_ADMIN_PASS

    def admin_conn(self):
        return mysql.connector.connect(
            host=self.host,
            user=self.admin_user,
            password=self.admin_pass
        )

    def app_conn(self):
        return mysql.connector.connect(
            host=self.host,
            user=self.admin_user,
            password=self.admin_pass,
            database="user_db"
        )

    def user_conn(self, username, password):
        return mysql.connector.connect(
            host=self.host,
            user=username,
            password=password
        )

    def create_mysql_user(self, username, password):
        db = self.admin_conn()
        cursor = db.cursor()

        # Tao user
        cursor.execute(f"CREATE USER IF NOT EXISTS '{username}'@'%' IDENTIFIED BY '{password}'")
        db.commit()

        cursor.close()
        db.close()

    def create_user_db(self, username, db_name):
        db = self.admin_conn()
        cursor = db.cursor()

        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
        cursor.execute(f"""
               GRANT ALL PRIVILEGES 
               ON {db_name}.* TO '{username}'@'%';
        """)
        cursor.execute('FLUSH PRIVILEGES')

        db.commit()
        cursor.close()
        db.close()

        return db_name

    def delete_mysql_user(self, username, password):
        # 1. Log vào user -> xoá db của user
        user_db = self.user_conn(username, password)
        cursor = user_db.cursor()
        admin_db = self.admin_conn()
        admin_cursor = admin_db.cursor()


        cursor.execute('SHOW DATABASES')
        databases = [
            db[0] for db in cursor.fetchall()
            if db[0] not in ("information_schema", "mysql", "sys", "performance_schema")
        ]

        for db_name in databases:
            cursor.execute(f"DROP DATABASE `{db_name}`")

        user_db.commit()
        cursor.close()
        user_db.close()

        # 2. Xoá account user
        admin_cursor.execute(f"DROP USER IF EXISTS '{username}'@'%'")
        admin_cursor.execute('FLUSH PRIVILEGES')

        admin_db.commit()
        admin_cursor.close()
        admin_db.close()
