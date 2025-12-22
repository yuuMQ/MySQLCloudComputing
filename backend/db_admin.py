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
