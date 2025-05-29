# CTGOV Compliance Web Application

This directory contains a sample multitenant Django application with
supporting services.

## Components

- **Django** application located in `ctgovapp/`.
- **PostgreSQL** for application data.
- **Flyway** for database migrations.
- **Blazegraph** for graph data with a script to load mock trials.
- Connection placeholders for **AWS Neptune**.

## Usage

```bash
cd scripts
./setup.sh
```

The setup script is idempotent. It starts the containers, runs Flyway and
Django migrations and loads mock data into Blazegraph.
