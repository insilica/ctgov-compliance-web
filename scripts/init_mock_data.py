import os
import hashlib
import psycopg2
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).parent))
from populate_blazegraph import insert_mock_data


def get_conn():
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=os.environ.get('DB_PORT', '5464'),
        dbname=os.environ.get('DB_NAME', 'ctgov-web'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', 'devpassword'),
    )


def hash_pwd(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def populate_postgres():
    conn = get_conn()
    cur = conn.cursor()

    # organizations
    cur.execute("INSERT INTO organization (name) VALUES (%s) RETURNING id", ("Acme Health",))
    org1_id = cur.fetchone()[0]
    cur.execute("INSERT INTO organization (name) VALUES (%s) RETURNING id", ("Beta Clinic",))
    org2_id = cur.fetchone()[0]

    # users
    cur.execute(
        "INSERT INTO ctgov_user (email, password_hash) VALUES (%s, %s) RETURNING id",
        ("alice@example.com", hash_pwd("password")),
    )
    alice_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO ctgov_user (email, password_hash) VALUES (%s, %s) RETURNING id",
        ("bob@example.com", hash_pwd("password")),
    )
    bob_id = cur.fetchone()[0]

    # memberships
    cur.execute(
        "INSERT INTO user_organization (user_id, organization_id, role) VALUES (%s, %s, %s)",
        (alice_id, org1_id, "clinician"),
    )
    cur.execute(
        "INSERT INTO user_organization (user_id, organization_id, role) VALUES (%s, %s, %s)",
        (bob_id, org2_id, "clinician"),
    )

    # trials
    cur.execute(
        "INSERT INTO trial (nct_id, organization_id, title, start_date, completion_date) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        ("NCT00000001", org1_id, "Hypertension Study", "2022-01-01", "2023-01-01"),
    )
    trial1_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO trial (nct_id, organization_id, title, start_date, completion_date) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        ("NCT00000002", org2_id, "Diabetes Study", "2022-06-01", "2024-06-01"),
    )
    trial2_id = cur.fetchone()[0]

    # compliance entries
    cur.execute(
        "INSERT INTO trial_compliance (trial_id, status) VALUES (%s, %s)",
        (trial1_id, "on time"),
    )
    cur.execute(
        "INSERT INTO trial_compliance (trial_id, status) VALUES (%s, %s)",
        (trial2_id, "late"),
    )

    conn.commit()
    cur.close()
    conn.close()


def main():
    populate_postgres()
    insert_mock_data()


if __name__ == "__main__":
    main()
