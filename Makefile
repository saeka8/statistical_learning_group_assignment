.PHONY: up down logs migrate createsuperuser shell test test-cov lint format seed

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api worker

migrate:
	docker compose exec api python manage.py migrate

createsuperuser:
	docker compose exec api python manage.py createsuperuser

shell:
	docker compose exec api python manage.py shell_plus

test:
	docker compose exec api pytest

test-cov:
	docker compose exec api pytest --cov=apps --cov-report=term-missing

lint:
	docker compose exec api ruff check .

format:
	docker compose exec api ruff format .

seed:
	docker compose exec api python manage.py loaddata fixtures/sample_data.json
