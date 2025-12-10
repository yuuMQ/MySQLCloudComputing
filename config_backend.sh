sudo apt install python3-pip python3-venv -y

mkdir ~/MySQLCloudComputing
cd ~/MySQLCloudComputing

python3 -m venv venv

source venv/bin/activate

pip install Flask mysql-connector-python
