from flask import Flask
from authentication_services import AuthServices
from database_services import DatabaseServices
from table_services import TableServices
from key_services import KeyServices

app = Flask(__name__)
app.secret_key = "super-secret-key"

# TRANG CHỦ - SHOW DATABASES
# --------------------------- DATABASE SERVICES -----------------------
@app.route("/")
def index():
    return DatabaseServices.show_databases()

# TAO DATABASE
@app.route('/create_database', methods=['POST'])
def create_database():
    return DatabaseServices.create_database()

# XOA DATABASE
@app.route('/drop_database/<dbname>')
def drop_database(dbname):
    return DatabaseServices.drop_database(dbname)

# BACKUP

# RESTORE
@app.route('/restore', methods=['POST'])
def restore():
    return DatabaseServices.restore_database()


# --------------------------- AUTHENTICATION SERVICES -----------------------

# ĐĂNG KÝ TÀI KHOẢN
@app.route('/register', methods=['GET', 'POST'])
def register():
    return AuthServices.register()

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    return AuthServices.login()

# LOGOUT
@app.route('/logout')
def logout():
    return AuthServices.logout()


# --------------------------- TABLES SERVICES -----------------------

# TAO TABLE
@app.route('/database/<dbname>/create_table', methods=['POST'])
def create_table(dbname):
    return TableServices.create_table(dbname)

# DROP TABLE
@app.route('/database/<dbname>/drop_table/<table>')
def drop_table(dbname, table):
    return TableServices.drop_table(dbname, table)

# SHOW TABLES
@app.route('/database/<dbname>')
def list_tables(dbname):
   return TableServices.list_tables(dbname)

# SELECT
@app.route('/database/<dbname>/<table>')
def view_table(dbname, table):
    return TableServices.view_table(dbname, table)

# ADD COLUMN
@app.route('/database/<dbname>/<table>/add_column', methods=['POST'])
def add_column(dbname, table):
    return TableServices.add_column(dbname, table)

# GET COLUMN
@app.route("/database/<dbname>/table/<table>/columns")
def get_table_columns(dbname, table):
    return TableServices.get_table_columns(dbname, table)

# DROP COLUMN
@app.route('/database/<dbname>/<table>/drop_column', methods=['POST'])
def drop_column(dbname, table):
    return TableServices.drop_column(dbname, table)

# RENAME COLUMN
@app.route('/database/<dbname>/<table>/rename_column', methods=['POST'])
def rename_column(dbname, table):
    return TableServices.rename_column(dbname, table)

# ADD ROW
@app.route('/database/<dbname>/<table>/add_row', methods=['POST'])
def add_row(dbname, table):
    return TableServices.add_row(dbname, table)

# EDIT ROW
@app.route('/database/<dbname>/<table>/edit_row/<rowid>', methods=['POST'])
def edit_row(dbname, table, rowid):
    return TableServices.edit_row(dbname, table, rowid)

# DELETE ROW
@app.route('/database/<dbname>/<table>/delete_row/<rowid>')
def delete_row(dbname, table, rowid):
    return TableServices.delete_row(dbname, table, rowid)


# --------------------------- KEY SERVICES -------------------

# ADD PRIMARY KEY
@app.route('/database/<dbname>/<table>/add_primary_key', methods=['POST'])
def add_primary_key(dbname, table):
    return KeyServices.add_primary_key(dbname, table)

# DROP PRIMARY KEY
@app.route('/database/<dbname>/<table>/drop_primary_key', methods=['POST'])
def drop_primary_key(dbname, table):
    return KeyServices.drop_primary_key(dbname, table)

# ADD FOREIGN KEY
@app.route('/database/<dbname>/<table>/add_foreign_key', methods=['POST'])
def add_foreign_key(dbname, table):
    return KeyServices.add_foreign_key(dbname, table)

@app.route('/database/<dbname>/<table>/drop_foreign_key', methods=['POST'])
def drop_foreign_key(dbname, table):
    return KeyServices.drop_foreign_key(dbname, table)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)