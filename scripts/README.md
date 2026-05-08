# Scripts
This folder contains utility scripts for the BMIS backend.

## Available Scripts

### Seed Database
Populates the database with initial required data (admin users, etc.)

```sh
python -m scripts.seed
```

> Run this **after** running `alembic upgrade head`.
