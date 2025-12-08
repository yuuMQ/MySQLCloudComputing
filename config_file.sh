#!/bin/bash

sudo apt update
sudo apt install mysql-server -y

sudo apt install python3-pip python3-venv -y
mkdir ~/my_python_app
cd ~/my_python_app

python3 -m venv venv

source venv/bin/activate

pip install Flask mysql-connector-python