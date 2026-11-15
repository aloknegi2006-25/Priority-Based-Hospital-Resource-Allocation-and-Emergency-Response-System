
from getpass import getpass
from werkzeug.security import generate_password_hash
from database.db import execute_query

TEMP_PASSWORD = getpass("Enter temporary password for new staff accounts: ")

if not TEMP_PASSWORD:
    raise ValueError("Temporary password cannot be empty.")

staff_members = execute_query(
    """
    SELECT staff_id, employee_id, role
    FROM staff
    WHERE is_active = 1
    """,
    fetch="all"
)

created = 0
skipped = 0

for staff in staff_members:
    username = staff["employee_id"]

    existing = execute_query(
        "SELECT user_id FROM users WHERE staff_id = %s",
        (staff["staff_id"],),
        fetch="one"
    )

    if existing:
        print(f"Skipped: {username} (account already exists)")
        skipped += 1
        continue

    role = "DOCTOR" if staff["role"] == "DOCTOR" else "STAFF"

    execute_query(
        """
        INSERT INTO users (staff_id, username, password_hash, role)
        VALUES (%s, %s, %s, %s)
        """,
        (
            staff["staff_id"],
            username,
            generate_password_hash(TEMP_PASSWORD),
            role
        )
    )

    print(f"Created: {username} ({role})")
    created += 1

print(f"\nFinished! Created: {created}, Skipped: {skipped}")
