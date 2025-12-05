mig:
	python manage.py makemigrations

up:
	python manage.py migrate

sup:
	python manage.py createsupseruser

flake:
	flake8 .

test:
	pytest -v

drop_db:
	docker exec -itu postgres 9f psql -c "DROP DATABASE ecommerce"

drop_test_db:
	docker exec -itu postgres 9f psql -c "DROP DATABASE test_ecommerce"

create_db:
	docker exec -itu postgres 9f psql -c "CREATE DATABASE ecommerce"

celery:
	celery -A root worker --loglevel=info

redis:
	docker start 72