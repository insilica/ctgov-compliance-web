# CTGOV Compliance Web Application

This project provides a basic Flask web interface for viewing clinical
trial compliance information.  It also includes supporting scripts and
database services.

## Components

- **Flask** application located in `web/`.
- **PostgreSQL** for application data.
- **Flyway** for database migrations.
- **Blazegraph** for graph data with a script to load mock trials.
- Connection placeholders for **AWS Neptune**.

## Usage

```bash
cd scripts
./setup.sh
```

The setup script is idempotent. It starts the containers, runs Flyway
migrations and loads mock data into Blazegraph.

### Mock Data

For convenience a helper script is included to load mock organizations,
users, trials and compliance information into both PostgreSQL and Blazegraph.

```bash
python scripts/init_mock_data.py
```

### Running the Flask App

After the services are running and mock data is loaded you can start the
development server:

```bash
flask run --host 0.0.0.0 --port 6513
```
