#!/bin/bash

MYSQL_HOST="db-cloud.cemrtuenvgdj.us-east-1.rds.amazonaws.com"
MYSQL_ADMIN_USER="admin"
MYSQL_ADMIN_PASS="admin123"

APP_USERNAME="$1"
APP_PASSWORD="$2"

DB_NAME="db_${APP_USERNAME}"

mysql -h $MYSQL_HOST -u $MYSQL_ADMIN_USER -p$MYSQL_ADMIN_PASS <<EOF

-- Tạo user MySQL cho user ứng dụng
CREATE USER IF NOT EXISTS '$APP_USERNAME'@'%' IDENTIFIED BY '$APP_PASSWORD';

-- Tạo database riêng cho user
CREATE DATABASE IF NOT EXISTS $DB_NAME;

-- Cấp quyền ONLY database riêng
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$APP_USERNAME'@'%';

-- Cấm user này xem database khác
GRANT SELECT ON performance_schema.user_variables_by_thread TO '$APP_USERNAME'@'%';

-- Thu hồi quyền xem metadata
REVOKE SHOW DATABASES ON *.* FROM '$APP_USERNAME'@'%';

FLUSH PRIVILEGES;

EOF

echo "User $APP_USERNAME created with database $DB_NAME"

