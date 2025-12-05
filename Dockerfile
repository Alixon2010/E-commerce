FROM ghcr.io/astral-sh/uv:python3.12-alpine

WORKDIR /app

COPY ./ /app

RUN uv sync

CMD ["uv", "run", "python3", "manage.py", "runserver", "0:8006"]

# docker build -t p31_drf_image .
# docker run --name p31_container -p 8006:8000 -d p31_drf_image
# docker exec -it p31_container sh
# docker cp
# uv run python3 manage.py migrate

# docker exec -it p31_container sh -c 'uv run python3 manage.py migrate'
# docker exec -it p31_container sh -c 'uv run python3 manage.py createsuperuser --username admin'

# docker tag p31_drf_image kholmumin/p31_drf_image
# docker push kholmumin/p31_drf_image
# docker run --name p31_container -p 8006:8000 -d kholmumin/p31_drf_image

# uv, dockerhub