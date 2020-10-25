FROM python:3

WORKDIR /app

RUN pip install --no-cache-dir phonenumbers mysqlclient validate_email django-ninja filetype; mkdir -p /tmp/media; mkdir -p /tmp/media/cv; mkdir -p /tmp/media/logo;

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:80"]