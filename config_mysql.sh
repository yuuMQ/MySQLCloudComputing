#!/bin/bash

sudo apt update
sudo apt install mysql-server -y

sudo sed -i 's/^.*bind-address.*/bind-address = 0.0.0.0/' /etc/mysql/mysql.conf.d/mysqld.cnf
sudo systemctl restart mysql

sudo mysql <<EOF
-- create admin account
CREATE USER IF NOT EXISTS 'admin'@'%' IDENTIFIED BY 'admin123';

GRANT ALL PRIVILEGES ON *.* TO 'admin'@'%' WITH GRANT OPTION;

-- create user_db
CREATE DATABASE IF NOT EXISTS user_db;

USE user_db;

-- create table users
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users(username, password) VALUES ('admin', 'admin123');
FLUSH PRIVILEGES;

EOF
