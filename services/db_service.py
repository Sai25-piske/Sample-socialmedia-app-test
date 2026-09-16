import os
import mysql.connector
from mysql.connector import Error


def get_db():

    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(
            os.getenv(
                "MYSQL_PORT",
                3306
            )
        ),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )


def init_db():

    db = None
    cursor = None

    try:

        db = get_db()
        cursor = db.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (

                id INT AUTO_INCREMENT PRIMARY KEY,

                username VARCHAR(50)
                    NOT NULL UNIQUE,

                email VARCHAR(150)
                    NOT NULL UNIQUE,

                password_hash VARCHAR(255)
                    NOT NULL,

                bio VARCHAR(255)
                    DEFAULT '',

                profile_pic VARCHAR(500)
                    DEFAULT NULL,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (

                id INT AUTO_INCREMENT PRIMARY KEY,

                user_id INT NOT NULL,

                image_key VARCHAR(500)
                    NOT NULL,

                caption VARCHAR(500)
                    DEFAULT '',

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS likes (

                id INT AUTO_INCREMENT PRIMARY KEY,

                user_id INT NOT NULL,

                post_id INT NOT NULL,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                UNIQUE KEY unique_like
                    (user_id, post_id),

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (post_id)
                    REFERENCES posts(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (

                id INT AUTO_INCREMENT PRIMARY KEY,

                user_id INT NOT NULL,

                post_id INT NOT NULL,

                comment TEXT NOT NULL,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (post_id)
                    REFERENCES posts(id)
                    ON DELETE CASCADE
            )
        """)

        db.commit()

        print("Database initialized successfully.")

    except Error as e:

        print(
            f"Database initialization error: {e}"
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()
