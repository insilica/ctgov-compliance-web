import os
import sys
import pathlib
from datetime import date, timedelta
from typing import List
import psycopg2
from werkzeug.security import generate_password_hash
import random

# Optional: CLI for flexibility
import argparse


# --- Configuration ---
NUM_ORGANIZATIONS = 5
NUM_USERS = 2  # default number of users
NUM_TRIALS = 5000
DEFAULT_PASSWORD = "password"

# --- Database Connection ---
def get_conn():
    """Establish a connection to the Postgres database using environment variables or defaults."""
    return psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=os.environ.get('DB_PORT', '5464'),
        dbname=os.environ.get('DB_NAME', 'ctgov-web'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', 'devpassword'),
    )

# --- Utility Functions ---
def hash_pwd(password: str) -> str:
    """Hash a password for storing in the database."""
    return generate_password_hash(password)

# --- Data Population Functions ---
def populate_organizations(cur, num_orgs: int = NUM_ORGANIZATIONS) -> List[int]:
    """Insert organizations if not present. Return their IDs."""
    print(f"Seeding {num_orgs} organizations...")
    org_ids = []
    for i in range(num_orgs):
        org_name = f"Organization {i+1}"
        org_email_domain = f"organization{i+1}.com"
        cur.execute("SELECT id FROM organization WHERE name = %s", (org_name,))
        result = cur.fetchone()
        if not result:
            cur.execute(
                "INSERT INTO organization (name, email_domain) VALUES (%s, %s) RETURNING id",
                (org_name, org_email_domain)
            )
            org_id = cur.fetchone()[0]
        else:
            org_id = result[0]
        org_ids.append(org_id)
        print(f"  Organization {i+1}/{num_orgs} seeded", end='\r')
    print(f"  Done seeding organizations.{' ' * 30}")
    return org_ids

def populate_users(cur, num_users: int = NUM_USERS) -> List[int]:
    """Insert users (user1@example.com, user2@example.com, ...) if not present. Return their IDs."""
    print(f"Seeding {num_users} users...")
    user_ids = []
    for i in range(num_users):
        email = f"user{i+1}@example.com"
        cur.execute("SELECT id FROM ctgov_user WHERE email = %s", (email,))
        result = cur.fetchone()
        if not result:
            cur.execute(
                "INSERT INTO ctgov_user (email, password_hash) VALUES (%s, %s) RETURNING id",
                (email, hash_pwd(DEFAULT_PASSWORD)),
            )
            user_id = cur.fetchone()[0]
        else:
            user_id = result[0]
        user_ids.append(user_id)
        print(f"  User {i+1}/{num_users} seeded", end='\r')
    print(f"  Done seeding users.{' ' * 30}")
    return user_ids

def populate_login_activity(cur, user_ids: List[int]) -> None:
    """Insert a login activity record for each user."""
    print(f"Seeding login activity for {len(user_ids)} users...")
    for idx, user_id in enumerate(user_ids):
        cur.execute(
            "INSERT INTO login_activity (user_id) VALUES (%s)", (user_id,)
        )
        print(f"  Login activity {idx+1}/{len(user_ids)}", end='\r')
    print(f"  Done seeding login activity.{' ' * 30}")

def populate_user_organizations(cur, user_ids: List[int], org_ids: List[int]) -> None:
    """Assign each user to each organization with a role."""
    print(f"Seeding user-organization memberships ({len(user_ids)} users x {len(org_ids)} orgs)...")
    roles = ["clinician", "researcher", "admin", "monitor", "sponsor"]
    total = len(user_ids) * len(org_ids)
    count = 0
    for i, org_id in enumerate(org_ids):
        for j, user_id in enumerate(user_ids):
            cur.execute(
                "SELECT 1 FROM user_organization WHERE user_id = %s AND organization_id = %s",
                (user_id, org_id)
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO user_organization (user_id, organization_id, role) VALUES (%s, %s, %s)",
                    (user_id, org_id, roles[(i + j) % len(roles)])
                )
            count += 1
            print(f"  Membership {count}/{total} ({count/total*100:.2f}%)", end='\r')
    print(f"  Done seeding user-organization memberships.{' ' * 30}")

def populate_trials_and_compliance(cur, user_ids: List[int], org_ids: List[int], num_trials: int = NUM_TRIALS) -> None:
    """Insert mock trials and compliance records with random compliance rates per org and user."""
    print(f"Seeding {num_trials} trials and compliance records...")
    # Assign a random compliance rate to each org and user
    org_compliance_rates = {org_id: random.uniform(0.1, 0.9) for org_id in org_ids}
    user_compliance_rates = {user_id: random.uniform(0.1, 0.9) for user_id in user_ids}

    for i in range(num_trials):
        nct_id = f"NCT{i:08d}"
        org_id = org_ids[i % len(org_ids)]
        title = f"Study {i+1}"
        start_date = date(2022, 1, 1) + timedelta(days=i+1)
        end_date = start_date + timedelta(days=2)
        due_date = end_date + timedelta(days=1)
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
            # Use the average of org and user compliance rates for this trial
            compliance_rate = (org_compliance_rates[org_id] + user_compliance_rates[user_id]) / 2
            status = "Compliant" if random.random() < compliance_rate else "Incompliant"
            cur.execute(
                "INSERT INTO trial_compliance (trial_id, status) VALUES (%s, %s)",
                (trial_id, status)
            )
        print(f"  Trials/compliance {i+1}/{num_trials} ({((i+1)/num_trials)*100:.2f}%)", end='\r')
    print(f"  Done seeding trials and compliance.{' ' * 30}")

# --- Main Population Routine ---
def populate_postgres(num_orgs: int, num_users: int, num_trials: int) -> None:
    """Populate the Postgres database with mock data."""
    print("\n=== Begin populating Postgres database with mock data ===\n")
    conn = get_conn()
    cur = conn.cursor()

    org_ids = populate_organizations(cur, num_orgs)
    user_ids = populate_users(cur, num_users)
    populate_login_activity(cur, user_ids)
    populate_user_organizations(cur, user_ids, org_ids)
    populate_trials_and_compliance(cur, user_ids, org_ids, num_trials)

    cur.execute("REFRESH MATERIALIZED VIEW joined_trials;")
    cur.execute("REFRESH MATERIALIZED VIEW compare_orgs;")
    
    conn.commit()
    cur.close()
    conn.close()
    print("\n=== Completed populating Postgres database with mock data ===\n")

# --- CLI Entrypoint ---
def main():
    parser = argparse.ArgumentParser(description="Populate Postgres with mock data.")
    parser.add_argument('--orgs', type=int, default=NUM_ORGANIZATIONS, help='Number of organizations to create')
    parser.add_argument('--users', type=int, default=NUM_USERS, help='Number of users to create')
    parser.add_argument('--trials', type=int, default=NUM_TRIALS, help='Number of trials to create')
    args = parser.parse_args()

    populate_postgres(args.orgs, args.users, args.trials)



if __name__ == "__main__":
    main()
