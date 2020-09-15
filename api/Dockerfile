FROM python:3

WORKDIR /app

RUN pip install --no-cache-dir phonenumbers mariadb validate_email django-ninja


COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:80"]