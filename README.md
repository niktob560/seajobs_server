# Seajobs project backend

## How to run an API:
1. Set DB and e-mail credentials in ``$project/api/seajobs_server/urls.py``
2. Run ``python $project/api/manage.py runserver``
3. Be awesome

## How to start full backend using docker-compose:
Run
```
docker-compose up -d
```
And then there wil be:  
``mariadb`` on ``3308``  
``API`` on ``8000``  
``Nginx`` on ``8080``  
``Nginx`` will proxy all ``/api/`` requests into ``API`` container (for example, ``0.0.0.0/api/login`` will be proxied into ``API/api/login``)
