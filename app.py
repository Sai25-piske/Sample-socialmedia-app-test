from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

from services.db_service import get_db
from services.s3_service import (
    upload_image,
    generate_presigned_url,
    delete_image,
    check_storage,
    StorageError
)


# --------------------------------------------------
# Flask Configuration
# --------------------------------------------------

app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "change-this-secret-key"
)

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


# --------------------------------------------------
# Allowed Image Extensions
# --------------------------------------------------

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp"
}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def validate_upload(file):
    if not file or not file.filename:
        return "No image selected"

    if not allowed_file(file.filename):
        return "Use JPG, JPEG, PNG, GIF, or WEBP images"

    file.stream.seek(0, os.SEEK_END)
    file_size = file.stream.tell()
    file.stream.seek(0)

    if file_size > MAX_UPLOAD_BYTES:
        return "Images must be 15 MB or smaller"

    return None


@app.errorhandler(413)
def request_too_large(error):
    return "The image is too large. Please choose an image up to 15 MB.", 413


# --------------------------------------------------
# Current User Helper
# --------------------------------------------------

def current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    db = None
    cursor = None

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, username, email, bio, profile_pic
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        return cursor.fetchone()

    except Exception as e:
        print(f"Current user error: {e}")
        return None

    finally:
        if cursor:
            cursor.close()

        if db:
            db.close()


# --------------------------------------------------
# Make Current User Available in Templates
# --------------------------------------------------

@app.context_processor
def inject_user():

    user = current_user()

    profile_url = None

    if user and user.get("profile_pic"):
        try:
            profile_url = generate_presigned_url(
                user["profile_pic"]
            )
        except Exception as e:
            print(f"Profile URL error: {e}")

    return {
        "current_user": user,
        "current_user_profile_url": profile_url
    }


# --------------------------------------------------
# HOME / FEED
# --------------------------------------------------

@app.route("/")
def feed():

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = None
    cursor = None

    try:

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                posts.id,
                posts.user_id,
                posts.image_key,
                posts.caption,
                posts.created_at,
                users.username,
                users.profile_pic
            FROM posts
            JOIN users
                ON posts.user_id = users.id
            ORDER BY posts.created_at DESC
            """
        )

        posts = cursor.fetchall()

        for post in posts:

            # Post image URL
            try:
                post["image_url"] = generate_presigned_url(
                    post["image_key"]
                )
            except Exception:
                post["image_url"] = None

            # Profile image URL
            if post.get("profile_pic"):
                try:
                    post["profile_url"] = generate_presigned_url(
                        post["profile_pic"]
                    )
                except Exception:
                    post["profile_url"] = None
            else:
                post["profile_url"] = None

            # Like count
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM likes
                WHERE post_id = %s
                """,
                (post["id"],)
            )

            post["like_count"] = cursor.fetchone()["count"]

            # Comment count
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM comments
                WHERE post_id = %s
                """,
                (post["id"],)
            )

            post["comment_count"] = cursor.fetchone()["count"]

            # Whether current user liked the post
            cursor.execute(
                """
                SELECT id
                FROM likes
                WHERE user_id = %s
                AND post_id = %s
                """,
                (
                    session["user_id"],
                    post["id"]
                )
            )

            post["liked"] = cursor.fetchone() is not None

        return render_template(
            "feed.html",
            posts=posts
        )

    except Exception as e:

        print(f"Feed error: {e}")

        return "Unable to load feed", 500

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# --------------------------------------------------
# REGISTER
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get(
        "username",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    if not username or not email or not password:
        return "All fields are required", 400

    if len(password) < 6:
        return "Password must be at least 6 characters", 400

    db = None
    cursor = None

    try:

        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Check existing user
        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = %s
            OR email = %s
            """,
            (
                username,
                email
            )
        )

        existing_user = cursor.fetchone()

        if existing_user:
            return "Username or email already exists", 409

        password_hash = generate_password_hash(
            password
        )

        cursor.execute(
            """
            INSERT INTO users
            (
                username,
                email,
                password_hash
            )
            VALUES
            (
                %s,
                %s,
                %s
            )
            """,
            (
                username,
                email,
                password_hash
            )
        )

        db.commit()

        return redirect(
            url_for("login")
        )

    except Exception as e:

        if db:
            db.rollback()

        print(f"Registration error: {e}")

        return "Registration failed", 500

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )

    db = None
    cursor = None

    try:

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE username = %s
            """,
            (username,)
        )

        user = cursor.fetchone()

        if not user:
            return "Invalid username or password", 401

        if not check_password_hash(
            user["password_hash"],
            password
        ):
            return "Invalid username or password", 401

        session["user_id"] = user["id"]
        session["username"] = user["username"]

        return redirect(
            url_for("feed")
        )

    except Exception as e:

        print(f"Login error: {e}")

        return "Login failed", 500

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# --------------------------------------------------
# UPLOAD POST
# --------------------------------------------------

@app.route("/upload", methods=["GET", "POST"])
def upload():

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    if request.method == "GET":
        return render_template("upload.html")

    file = request.files.get("image")

    caption = request.form.get(
        "caption",
        ""
    ).strip()

    upload_error = validate_upload(file)
    if upload_error:
        return upload_error, 400

    try:

        # Upload image to S3
        image_key = upload_image(
            file,
            folder="uploads"
        )

    except Exception as e:

        error_code = getattr(e, "code", type(e).__name__)
        print(f"S3 upload error ({error_code}): {e}")

        return f"Image upload failed ({error_code}). Check the S3 bucket configuration and permissions.", 500

    db = None
    cursor = None

    try:

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO posts
            (
                user_id,
                image_key,
                caption
            )
            VALUES
            (
                %s,
                %s,
                %s
            )
            """,
            (
                session["user_id"],
                image_key,
                caption
            )
        )

        db.commit()

        return redirect(
            url_for("feed")
        )

    except Exception as e:

        if db:
            db.rollback()

        print(f"Post database error: {e}")

        # Delete uploaded S3 image if DB insert fails
        try:
            delete_image(image_key)
        except Exception:
            pass

        return "Post creation failed", 500

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# --------------------------------------------------
# LIKE / UNLIKE
# --------------------------------------------------

@app.route(
    "/like/<int:post_id>",
    methods=["POST"]
)
def like_post(post_id):

    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Login required"
        }), 401

    db = None
    cursor = None

    try:

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id
            FROM likes
            WHERE user_id = %s
            AND post_id = %s
            """,
            (
                session["user_id"],
                post_id
            )
        )

        existing_like = cursor.fetchone()

        if existing_like:

            cursor.execute(
                """
                DELETE FROM likes
                WHERE user_id = %s
                AND post_id = %s
                """,
                (
                    session["user_id"],
                    post_id
                )
            )

            liked = False

        else:

            cursor.execute(
                """
                INSERT INTO likes
                (
                    user_id,
                    post_id
                )
                VALUES
                (
                    %s,
                    %s
                )
                """,
                (
                    session["user_id"],
                    post_id
                )
            )

            liked = True

        db.commit()

        cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM likes
            WHERE post_id = %s
            """,
            (post_id,)
        )

        like_count = cursor.fetchone()["count"]

        return jsonify({
            "success": True,
            "liked": liked,
            "like_count": like_count
        })

    except Exception as e:

        if db:
            db.rollback()

        print(f"Like error: {e}")

        return jsonify({
            "success": False,
            "message": "Unable to update like"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# --------------------------------------------------
# COMMENT
# --------------------------------------------------

@app.route(
    "/comment/<int:post_id>",
    methods=["POST"]
)
def comment(post_id):

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    comment_text = request.form.get(
        "comment",
        ""
    ).strip()

    if not comment_text:
        return redirect(
            url_for("feed")
        )

    db = None
    cursor = None

    try:

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO comments
            (
                user_id,
                post_id,
                comment
            )
            VALUES
            (
                %s,
                %s,
                %s
            )
            """,
            (
                session["user_id"],
                post_id,
                comment_text
            )
        )

        db.commit()

        return redirect(
            url_for("feed")
        )

    except Exception as e:

        if db:
            db.rollback()

        print(f"Comment error: {e}")

        return "Unable to add comment", 500

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# --------------------------------------------------
# PROFILE
# --------------------------------------------------

@app.route("/profile/<username>")
def profile(username):

    db = None
    cursor = None

    try:

        db = get_db()
        cursor = db.cursor(dictionary=True)

        # User
        cursor.execute(
            """
            SELECT
                id,
                username,
                email,
                bio,
                profile_pic,
                created_at
            FROM users
            WHERE username = %s
            """,
            (username,)
        )

        user = cursor.fetchone()

        if not user:
            return "User not found", 404

        # Profile picture
        if user.get("profile_pic"):

            try:
                user["profile_url"] = generate_presigned_url(
                    user["profile_pic"]
                )
            except Exception:
                user["profile_url"] = None

        else:
            user["profile_url"] = None

        # Posts
        cursor.execute(
            """
            SELECT
                id,
                image_key,
                caption,
                created_at
            FROM posts
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user["id"],)
        )

        posts = cursor.fetchall()

        for post in posts:

            try:
                post["image_url"] = generate_presigned_url(
                    post["image_key"]
                )
            except Exception:
                post["image_url"] = None

        # Post count
        cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM posts
            WHERE user_id = %s
            """,
            (user["id"],)
        )

        post_count = cursor.fetchone()["count"]

        return render_template(
            "profile.html",
            user=user,
            posts=posts,
            post_count=post_count
        )

    except Exception as e:

        print(f"Profile error: {e}")

        return "Unable to load profile", 500

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# --------------------------------------------------
# EDIT PROFILE
# --------------------------------------------------

@app.route(
    "/edit-profile",
    methods=["GET", "POST"]
)
def edit_profile():

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    db = None
    cursor = None

    try:

        db = get_db()
        cursor = db.cursor(dictionary=True)

        if request.method == "GET":

            cursor.execute(
                """
                SELECT
                    id,
                    username,
                    email,
                    bio,
                    profile_pic
                FROM users
                WHERE id = %s
                """,
                (session["user_id"],)
            )

            user = cursor.fetchone()

            if user and user.get("profile_pic"):
                try:
                    user["profile_url"] = generate_presigned_url(
                        user["profile_pic"]
                    )
                except Exception:
                    user["profile_url"] = None

            return render_template(
                "edit_profile.html",
                user=user
            )

        bio = request.form.get(
            "bio",
            ""
        ).strip()

        file = request.files.get(
            "profile_pic"
        )

        profile_pic = None

        if file and file.filename:

            upload_error = validate_upload(file)
            if upload_error:
                return upload_error, 400

            profile_pic = upload_image(
                file,
                folder="profiles"
            )

        if profile_pic:

            cursor.execute(
                """
                UPDATE users
                SET bio = %s,
                    profile_pic = %s
                WHERE id = %s
                """,
                (
                    bio,
                    profile_pic,
                    session["user_id"]
                )
            )

        else:

            cursor.execute(
                """
                UPDATE users
                SET bio = %s
                WHERE id = %s
                """,
                (
                    bio,
                    session["user_id"]
                )
            )

        db.commit()

        return redirect(
            url_for(
                "profile",
                username=current_user()["username"]
            )
        )

    except Exception as e:

        if db:
            db.rollback()

        print(f"Edit profile error: {e}")

        return "Unable to update profile", 500

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# --------------------------------------------------
# DELETE POST
# --------------------------------------------------

@app.route(
    "/delete/<int:post_id>",
    methods=["POST"]
)
def delete_post(post_id):

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    db = None
    cursor = None

    try:

        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Get post
        cursor.execute(
            """
            SELECT
                id,
                user_id,
                image_key
            FROM posts
            WHERE id = %s
            """,
            (post_id,)
        )

        post = cursor.fetchone()

        if not post:
            return "Post not found", 404

        # Only owner can delete
        if post["user_id"] != session["user_id"]:
            return "Unauthorized", 403

        # Delete DB record
        cursor.execute(
            """
            DELETE FROM posts
            WHERE id = %s
            """,
            (post_id,)
        )

        db.commit()

        # Delete S3 image
        try:
            delete_image(
                post["image_key"]
            )
        except Exception as e:
            print(f"S3 delete error: {e}")

        return redirect(
            url_for("feed")
        )

    except Exception as e:

        if db:
            db.rollback()

        print(f"Delete post error: {e}")

        return "Unable to delete post", 500

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.route("/health")
def health():

    db = None
    cursor = None

    try:

        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "SELECT 1"
        )

        cursor.fetchone()

        storage_status = "connected"
        storage_error = None
        try:
            check_storage()
        except StorageError as error:
            storage_status = "disconnected"
            storage_error = error.code

        response = {
            "status": "healthy",
            "database": "connected",
            "storage": storage_status
        }

        if storage_error:
            response["storage_error"] = storage_error

        return jsonify(response), 200 if storage_status == "connected" else 503

    except Exception as e:

        print(f"Health check error: {e}")

        return jsonify({
            "status": "unhealthy",
            "database": "disconnected"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# --------------------------------------------------
# START FLASK
# --------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
