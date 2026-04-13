# statistical_learning_group_assignment

## Getting Started

### Prerequisites

- [Docker Engine](https://docs.docker.com/engine/install/) (or Docker Desktop)
- `docker compose` plugin (`docker compose version` should work)
- `make` — install with `sudo apt install make` on Linux/WSL

### First-time setup

**1. Clone the repo and enter the directory**
```bash
git clone <repo-url>
cd statistical_learning_group_assignment
```

**2. Create your `.env` file**
```bash
cp .env.example .env
```
Open `.env` and set a real value for `SECRET_KEY`. Everything else can stay as-is for local development.

**3. Start all services**
```bash
make up
```
This builds the Docker images and starts PostgreSQL, MinIO, the Django API, and the background worker.

**4. Run database migrations**
```bash
make migrate
```

**5. Create an admin user** *(optional but useful)*
```bash
make createsuperuser
```

The API is now available at `http://localhost:8000/api/`  
The Django admin panel is at `http://localhost:8000/admin/`  
The MinIO console is at `http://localhost:9001` (login with `MINIO_USER` / `MINIO_PASSWORD` from your `.env`)

---

### Everyday commands

| Command | What it does |
|---|---|
| `make up` | Build and start all containers |
| `make down` | Stop all containers |
| `make logs` | Tail logs for the API and worker |
| `make migrate` | Run pending database migrations |
| `make shell` | Open a Django shell inside the container |
| `make test` | Run the test suite |
| `make lint` | Run the linter |

---

### Without make

If you don't have `make` installed you can run the underlying commands directly:

```bash
docker compose up --build -d       # make up
docker compose exec api python manage.py migrate   # make migrate
docker compose logs -f api worker  # make logs
docker compose down                # make down
```