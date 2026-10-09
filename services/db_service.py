import os
import mysql.connector
from mysql.connector import Error


def get_db():

    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "mysql"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "piskegram_user"),
        password=os.getenv("MYSQL_PASSWORD", "local-piskegram-password"),
        database=os.getenv("MYSQL_DATABASE", "piskegram")
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
            CREATE TABLE IF NOT EXISTS follows (

                follower_id INT NOT NULL,

                followed_id INT NOT NULL,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                PRIMARY KEY
                    (follower_id, followed_id),

                KEY idx_follows_followed_id
                    (followed_id),

                CONSTRAINT chk_follows_not_self
                    CHECK (follower_id <> followed_id),

                FOREIGN KEY (follower_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                FOREIGN KEY (followed_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
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
        raise

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()
