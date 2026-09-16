#!/bin/sh

echo "Starting PiskeGram..."

echo "Waiting for MySQL..."

python -c "
import time
import os
import mysql.connector

for i in range(30):
    try:
        conn = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE')
        )
        conn.close()
        print('MySQL is ready!')
        break
    except Exception as e:
        print('Waiting for MySQL...')
        time.sleep(2)
else:
    raise Exception('MySQL did not become ready')
"

echo "Initializing database..."

python -c "from services.db_service import init_db; init_db()"

echo "Starting Flask..."

python app.py
