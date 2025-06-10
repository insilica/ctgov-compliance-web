import os
from werkzeug.security import generate_password_hash
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
    return generate_password_hash(password)


def populate_postgres():
    conn = get_conn()
    cur = conn.cursor()

    # organizations
    org_ids = []
    for i in range(50):
        org_name = f"Organization {i+1}"
        cur.execute("SELECT id FROM organization WHERE name = %s", (org_name,))
        result = cur.fetchone()
        if not result:
            cur.execute("INSERT INTO organization (name) VALUES (%s) RETURNING id", (org_name,))
            org_id = cur.fetchone()[0]
        else:
            org_id = result[0]
        org_ids.append(org_id)

    # users
    cur.execute("SELECT id FROM ctgov_user WHERE email = %s", ("alice@example.com",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO ctgov_user (email, password_hash) VALUES (%s, %s) RETURNING id",
            ("alice@example.com", hash_pwd("password")),
        )
    cur.execute("SELECT id FROM ctgov_user WHERE email = %s", ("alice@example.com",))
    alice_id = cur.fetchone()[0]

    cur.execute("SELECT id FROM ctgov_user WHERE email = %s", ("bob@example.com",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO ctgov_user (email, password_hash) VALUES (%s, %s) RETURNING id",
            ("bob@example.com", hash_pwd("password")),
        )
    cur.execute("SELECT id FROM ctgov_user WHERE email = %s", ("bob@example.com",))
    bob_id = cur.fetchone()[0]

    # record sample login activity
    cur.execute(
        "INSERT INTO login_activity (user_id) VALUES (%s)", (alice_id,)
    )
    cur.execute(
        "INSERT INTO login_activity (user_id) VALUES (%s)", (bob_id,)
    )

    # memberships
    cur.execute("SELECT 1 FROM user_organization WHERE user_id = %s AND organization_id = %s",
                (alice_id, org_ids[0]))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO user_organization (user_id, organization_id, role) VALUES (%s, %s, %s)",
            (alice_id, org_ids[0], "clinician"),
        )

    cur.execute("SELECT 1 FROM user_organization WHERE user_id = %s AND organization_id = %s",
                (bob_id, org_ids[1]))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO user_organization (user_id, organization_id, role) VALUES (%s, %s, %s)",
            (bob_id, org_ids[1], "clinician"),
        )

    # trials and compliance entries
    from datetime import date, timedelta

    for i in range(50):
        nct_id = f"NCT{i:08d}"
        title = f"Study {i+1}"
        start_date = date(2022, 1, 1) + timedelta(days=i*30)
        end_date = start_date + timedelta(days=365)
        org_id = org_ids[i % len(org_ids)]

        cur.execute("SELECT id FROM trial WHERE nct_id = %s", (nct_id,))
        result = cur.fetchone()
        if not result:
            cur.execute(
                "INSERT INTO trial (nct_id, organization_id, title, start_date, completion_date) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (nct_id, org_id, title, start_date, end_date)
            )
            trial_id = cur.fetchone()[0]
        else:
            trial_id = result[0]

        cur.execute("SELECT 1 FROM trial_compliance WHERE trial_id = %s", (trial_id,))
        if not cur.fetchone():
            status = "on time" if i % 3 != 0 else "late"
            cur.execute(
                "INSERT INTO trial_compliance (trial_id, status) VALUES (%s, %s)",
                (trial_id, status)
            )

    conn.commit()
    cur.close()
    conn.close()


def main():
    populate_postgres()
    insert_mock_data()


if __name__ == "__main__":
    main()
