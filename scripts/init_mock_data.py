import os
from werkzeug.security import generate_password_hash
import psycopg2
import pathlib
import sys
from datetime import date, timedelta

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


def populate_organization(cur):
    org_ids = []
    for i in range(5):
        org_name = f"Organization {i+1}"
        org_email_domain = f"organization{i+1}.com"
        cur.execute("SELECT id FROM organization WHERE name = %s", (org_name,))
        result = cur.fetchone()
        if not result:
            cur.execute("INSERT INTO organization (name, email_domain) VALUES (%s, %s) RETURNING id", (org_name,org_email_domain))
            org_id = cur.fetchone()[0]
        else:
            org_id = result[0]
        org_ids.append(org_id)
    return org_ids

def populate_ctgov_user(cur):
    user_ids = []
    cur.execute("SELECT id FROM ctgov_user WHERE email = %s", ("alice@example.com",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO ctgov_user (email, password_hash) VALUES (%s, %s) RETURNING id",
            ("alice@example.com", hash_pwd("password")),
        )
    cur.execute("SELECT id FROM ctgov_user WHERE email = %s", ("alice@example.com",))
    alice_id = cur.fetchone()[0]
    user_ids.append(alice_id)

    cur.execute("SELECT id FROM ctgov_user WHERE email = %s", ("bob@example.com",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO ctgov_user (email, password_hash) VALUES (%s, %s) RETURNING id",
            ("bob@example.com", hash_pwd("password")),
        )
    cur.execute("SELECT id FROM ctgov_user WHERE email = %s", ("bob@example.com",))
    bob_id = cur.fetchone()[0]
    user_ids.append(bob_id)

    return user_ids

def populate_login_activity(cur, user_ids):
    # record sample login activity
    for user_id in user_ids:
        cur.execute(
            "INSERT INTO login_activity (user_id) VALUES (%s)", (user_id,)
        )

def populate_user_organization(cur, user_ids, org_ids):
    roles = ["clinician", "researcher", "admin", "monitor", "sponsor"]

    # memberships
    for i in range(len(org_ids)):
        cur.execute(
            "SELECT 1 FROM user_organization WHERE user_id = %s AND organization_id = %s",
            (user_ids[0], org_ids[i])
        )
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO user_organization (user_id, organization_id, role) VALUES (%s, %s, %s)",
                (user_ids[0], org_ids[i], roles[i % len(roles)])
            )

        cur.execute(
            "SELECT 1 FROM user_organization WHERE user_id = %s AND organization_id = %s",
            (user_ids[1], org_ids[i])
        )
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO user_organization (user_id, organization_id, role) VALUES (%s, %s, %s)",
                (user_ids[1], org_ids[i], roles[i % len(roles)])
            )

def populate_trials_and_compliance(cur, user_ids, org_ids):
    for i in range(5000):
        nct_id = f"NCT{i:08d}"
        org_id = org_ids[i % len(org_ids)]
        title = f"Study {i+1}"
        start_date = date(2022, 1, 1) + timedelta(days=i*30)
        end_date = start_date + timedelta(days=365)
        due_date = end_date + timedelta(days=30)
        user_id = user_ids[i % len(user_ids)]

        
        cur.execute("SELECT id FROM trial WHERE nct_id = %s", (nct_id,))
        result = cur.fetchone()
        if not result:
            cur.execute(
                "INSERT INTO trial (nct_id, organization_id, title, start_date, completion_date, reporting_due_date, user_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (nct_id, org_id, title, start_date, end_date, due_date, user_id)
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

def populate_postgres():
    print("Begin populating Postgres database with mock data...")

    conn = get_conn()
    cur = conn.cursor()

    org_ids = populate_organization(cur)
    user_ids = populate_ctgov_user(cur)
    populate_login_activity(cur, user_ids)
    populate_user_organization(cur, user_ids, org_ids)
    populate_trials_and_compliance(cur, user_ids, org_ids)

    conn.commit()
    cur.close()
    conn.close()

    print("Completed populating Postgres database with mock data.")


def main():
    populate_postgres()
    insert_mock_data()


if __name__ == "__main__":
    main()
