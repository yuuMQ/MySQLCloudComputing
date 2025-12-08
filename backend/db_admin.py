'''
    - Nhan du lieu -> tao user va cap quyen db_user cho user.
'''

import mysql.connector
from config import *

def admin_conn():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_ADMIN_USER,
        password=MYSQL_ADMIN_PASS
    )

def create_mysql_user(username, password):
    db = admin_conn()
    cursor = db.cursor()

    # Tao user
    cursor.execute(f"CREATE USER IF NOT EXISTS '{username}'@'%' IDENTIFIED BY '{password}'")
    db.commit()

    cursor.close()
    db.close()

def create_user_db(username):
    db_name = f"db_{username}"

    db = admin_conn()
    cursor = db.cursor()

    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")

    cursor.execute(f"""
        GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER
        ON {db_name}.* TO '{username}'@'%';
    """)


    cursor.execute('FLUSH PRIVILEGES')

    db.commit()
    cursor.close()
    db.close()

    return db_name