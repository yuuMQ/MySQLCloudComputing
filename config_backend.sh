#!/bin/bash

sudo apt update
sudo apt install mysql-server -y
sudo apt install python3-pip python3-venv -y

sudo apt install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx