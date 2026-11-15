from getpass import getpass
from werkzeug.security import generate_password_hash
from database.db import execute_query

username = input("Enter admin username: ").strip()
password = getpass("Enter admin password: ")

if not username or not password:
    print("Username and password cannot be empty.")
else:
    password_hash = generate_password_hash(password)

    execute_query(
        """
        INSERT INTO users (username, password_hash, role)
        VALUES (%s, %s, 'ADMIN')
        """,
        (username, password_hash)
    )

    print("Admin account created successfully!")