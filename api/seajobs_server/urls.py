"""seajobs_server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path("", views.home, name="home")
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path("", Home.as_view(), name="home")
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path("blog/", include("blog.urls"))
"""
# Django
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.http import HttpResponse, Http404, HttpResponseServerError
from django.core.exceptions import PermissionDenied


# Django-Ninja
from ninja import NinjaAPI
from ninja.security import HttpBearer

# storage
import mariadb
import pathlib
import os
import filetype

# input validity
from validate_email import validate_email
from datetime import datetime, timedelta, date
import re

# random and hashes
import hashlib
import time
import random
import secrets

# e-mail
import smtplib
import sys
import base64
from email.mime.text import MIMEText
from email.header    import Header


class AuthError(Exception):
    pass

class Mailto:
    addr: str
    name: str
    def __init__(self, addr: str, name: str):
        self.addr = addr
        self.name = name


def db():
    return mariadb.connect(
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME)

def query_db(query, args=(), one=False):
    cur = db().cursor()
    cur.execute(query, args)
    r = [dict((cur.description[i][0], value) \
               for i, value in enumerate(row)) for row in cur.fetchall()]
    cur.connection.close()
    return (r[0] if r else None) if one else r

api = NinjaAPI()

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        cursor = None
        connection = None
        try:
            connection = db()
            cursor = connection.cursor()
            cursor.execute("DELETE FROM tokens WHERE expire_at <= NOW()")
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.commit()
        data = query_db(f"SELECT owner, owner_type FROM tokens WHERE token='{token}' LIMIT 1", (), one=True)
        if data:
            return data

class AdminAuthBearer(HttpBearer):
    def authenticate(self, request, token):
        data = query_db(f"SELECT owner, owner_type FROM tokens WHERE token='{token}' AND owner='{settings.ADMIN_EMAIL}' LIMIT 1", (), one=True)
        if data:
            return data

@api.post("/register_sailor")
def register_sailor(request, name: str, password: str, email: str, birthday_date: str, mobile_phone: str, position: str):
    cursor = None
    connection = None
    try :
        if not mobile_phone or not validate_mobile_phone(mobile_phone):
            raise ValueError("Invalid phone number")
        if not password or password.__len__() < 4:
            raise ValueError("Password must contain at least 4 chars")
        if not email or not validate_email(email):
            raise ValueError("Email invalid")
        if not birthday_date:
            raise ValueError("Birthday date must be set")
        birthday_date = datetime.strptime(birthday_date, "%d.%m.%Y")
        birthday_date = "{Y}-{m}-{d}".format(Y=birthday_date.year, m=birthday_date.month, d=birthday_date.day)
        if not position:
            raise ValueError("Position must be set")
        name = name.strip()
        if not name or name.count(' ') < 1 or name.count(' ') > 5:
            raise ValueError("Name must be set" if not name else "Name field must contain name and surname")
        phone = mobile_phone
        tupl = generate_password_hash_and_salt(password)
        hash = tupl[0]
        salt = tupl[1]
        try:
            if query_db(f"SELECT email FROM companies WHERE email='{email}'"):
                raise Exception("Company with such email already exist")
            connection = db()
            cursor = connection.cursor()
            id = cursor.execute("INSERT INTO users(name, password, salt, email, birthday_date, mobile_phone, position) VALUES (?, ?, ?, ?, ?, ?, ?) LIMIT 1", (name, hash, salt, email, birthday_date, phone, position))
            connection.commit()
            cursor.close()
        except mariadb.Error as e:
            print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
            print(f"{e}")
            if f"{e}".startswith("Duplicate entry"):
                raise Exception("User with such email already exist")
            else:
                return HttpResponseServerError()
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok"}
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.commit()

@api.post("/request_register_company")
def request_register_company(request, company_name: str, password: str, website: str, mobile_phone: str, email: str, country: str, city: str, address: str):
    cursor = None
    connection = None
    try :
        if not mobile_phone or not validate_mobile_phone(mobile_phone):
            raise ValueError("Invalid phone number")
        if not password or password.__len__() < 4:
            raise ValueError("Password must contain at least 4 chars")
        if not email or not validate_email(email):
            raise ValueError("Email invalid")
        if not company_name:
            raise ValueError("Company name must be set")
        if not country:
            raise ValueError("Country must be set")
        if not city:
            raise ValueError("City must be set")
        if not address:
            raise ValueError("Address must be set")
        phone = mobile_phone
        tupl = generate_password_hash_and_salt(password)
        hash = tupl[0]
        salt = tupl[1]
        print(tupl)
        print(f"{hash}, {salt}")
        try:
            if query_db(f"SELECT email FROM users WHERE email='{email}'"):
                raise ValueError("User with such email already exist")
            if query_db(f"SELECT email FROM companies WHERE email='{email}'"):
                raise ValueError("Company with such email already exist")
            connection = db()
            cursor = connection.cursor()
            id = cursor.execute("INSERT INTO companies_requests(name, password, salt, website, mobile_phone, email, country, city, address) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) LIMIT 1", (company_name, hash, salt, website, phone, email, country, city, address))
            connection.commit()
            cursor.close()
        except mariadb.Error as e:
            print(f"{e}")
            if f"{e}".startswith("Duplicate entry"):
                raise ValueError("Company with such email already exist")
            else:
                return HttpResponseServerError()
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": f"{id}"}
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.commit()

@api.post("/login")
def login(request, email: str, password: str):
    cur = None
    connection = None
    try:
        if not email or not validate_email(email):
            raise ValueError("Email invalid")
        if not password or password.__len__() < 4:
            raise ValueError("Password invalid")

        info = query_db(f"SELECT * FROM ((SELECT password, salt, email, 'user' as 'type' FROM users) UNION (SELECT password, salt, email, 'company' FROM companies)) AS U WHERE U.email='{email}' LIMIT 1", one=True)
        if info and verify_password(password, info['password'], info['salt']):
            type = info['type']
        else:
            raise ValueError("Invalid credentails")

        token = secrets.token_hex(256)
        connection = db()
        cur = connection.cursor()
        expire_at = datetime.now() + timedelta(1)
        
        q = f"INSERT INTO tokens (owner_type, owner, token, expire_at) VALUES ('{type}', '{email}', '{token}', '{expire_at}') LIMIT 1"
        cur.execute(q, ())
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": { "token": f"{token}", "type": type }, "admin": True if email == settings.ADMIN_EMAIL else False }
    finally:
        if cur and cur != None:
            cur.close()
        if connection and connection != None:
            connection.commit()

@api.post("/get_profile_company", auth=AuthBearer())
def get_profile_company(request):
    try:
        auth = request.auth
        print(auth)
        if auth["owner_type"] != "company":
            raise ValueError("This is not a company account")
        email = auth["owner"]
        data = query_db(f"SELECT name, website, mobile_phone, email, country, city, address, logo_path FROM companies WHERE email='{email}' LIMIT 1", args=(), one=True)
        print(data)
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": data}

@api.post("/get_profile_user", auth=AuthBearer())
def get_profile_user(request):
    try:
        auth = request.auth
        print(auth)
        if auth["owner_type"] != "user":
            raise ValueError("This is not a user account")
        email = auth["owner"]
        data = query_db(f"SELECT name, email, DATE_FORMAT(birthday_date, '%d.%m.%Y') as birthday_date, mobile_phone, position FROM users WHERE email='{email}' LIMIT 1", args=(), one=True)
        print(data)
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": data}

def handle_uploaded_file(filename, file):
    with open(filename, "wb+") as destination:
        for chunk in file.chunks():
            destination.write(chunk)

def handle_remove_file(filepath):
    pathlib.Path.unlink(filepath)

@api.post("/upload_cv", auth=AuthBearer())
def upload_cv(request):
    print("AAA")
    con = None
    cur = None
    try:
        if request.auth["owner_type"] != "user":
            raise ValueError("Only sailor can upload CV")
        email = request.auth["owner"]
        file = request.FILES["cv"]
        if not file:
            raise ValueError("Uploaded file with field 'cv' not found")
        filename = secrets.token_hex(64)
        ext = f"{file}".split(".")[1]
        filename += f".{ext}"
        path = f"{settings.CV_ROOT}{filename}"
        handle_uploaded_file(path, file)
        oldname = query_db(f"SELECT name FROM files WHERE owner_type='user' AND owner='{email}'", one=True)
        con = db()
        cur = con.cursor()
        if oldname:
            cur.execute(f"UPDATE files SET name='{filename}' WHERE owner='{email}' LIMIT 1")
        else:
            cur.execute(f"INSERT INTO files (owner_type, owner, name) VALUES ('user', '{email}', '{filename}')")
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": filename}
    finally:
        if cur and cur != None:
            cur.close()
        if con and con != None:
            con.commit()

@api.post("/upload_logo", auth=AuthBearer())
def upload_logo(request):
    con = None
    cur = None
    try:
        if request.auth["owner_type"] != "company":
            raise ValueError("Only company can upload logo")
        file = request.FILES["logo"]
        if not file:
            raise ValueError("Uploaded file with field 'logo' not found")
        filename = secrets.token_hex(64)
        ext = file.name.split(".")[1]
        filename += f".{ext}"
        path = f"{settings.LOGO_ROOT}{filename}"
        handle_uploaded_file(path, file)
        email = request.auth["owner"]
        oldname = query_db(f"SELECT name FROM files WHERE owner_type='company' AND owner='{email}' LIMIT 1", one=True)
        con = db()
        cur = con.cursor()
        cur.execute(f"UPDATE companies SET logo_path='{filename}' WHERE email='{email}' LIMIT 1", ())
        if oldname:
            cur.execute(f"UPDATE files SET name='{filename}' WHERE owner='{email}' AND owner_type='company' LIMIT 1", ())
        else:
            cur.execute(f"INSERT INTO files (name, owner, owner_type) VALUES('{filename}', '{email}', 'company')", ())
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": f"{filename}"}
    finally:
        if cur and cur != None:
            cur.close()
        if con and con != None:
            con.commit()

@api.post("/add_vacation", auth=AuthBearer())
def add_vacation(request, position: str, salary: str, fleet_type: str, start_at: str, contract_duration: str, nationality: str, english_level: str, requierments: str, fleet_construct_year: int, fleet_dwt: str, fleet_gd_type: str, fleet_power: int):
    con = None
    cur = None
    try:
        if request.auth["owner_type"] != "company":
            raise ValueError("Only company can add vacation")
        if not position:
            raise ValueError("Bad position")
        # if salary < 0:
        #     raise ValueError("Salary can't be less than 0")
        if not fleet_type:
            raise ValueError("Bad fleet type")
        if not start_at:
            raise ValueError("Bad start date")
        # start_at = datetime.strptime(start_at, "%d.%m.%Y")
        # start_at = "{Y}-{m}-{d}".format(Y=start_at.year, m=start_at.month, d=start_at.day)
        # if contract_duration <= 0:
        #     raise ValueError("Contract duration can't be less than 1")
        if not nationality:
            raise ValueError("Bad nationality")
        if not english_level:
            raise ValueError("Bad english level")
        if not requierments:
            raise ValueError("Bad requierments")
        if fleet_construct_year < 1500:
            raise ValueError("Bad fleet construct year")
        if not fleet_dwt:
            raise ValueError("Bad fleet DWT")
        if not fleet_gd_type:
            raise ValueError("Bad GD value")
        if fleet_power <= 0:
            raise ValueError("Fleet power must be grater that 0")
        company_email = request.auth["owner"]
        post_date = datetime.now()
        post_date = post_date.strftime("%Y-%m-%d %H:%M:%S")
        print(f"{post_date}")
        con = db()
        cur = con.cursor()
        position = position.lower()
        cur.execute(f"INSERT INTO vacations (position, salary, fleet, start_at, contract_duration, company_email, post_date, english_level, nationality, requierments, fleet_construct_year, fleet_dwt, fleet_gd, fleet_power) VALUES('{position}', '{salary}', '{fleet_type}', '{start_at}', '{contract_duration}', '{company_email}', '{post_date}', '{english_level}', '{nationality}', '{requierments}', '{fleet_construct_year}', '{fleet_dwt}', '{fleet_gd_type}', '{fleet_power}')", ())
        cur.execute(f"DELETE FROM vacations WHERE post_date not between date_sub(now(), INTERVAL 1 WEEK) and now()", ())
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": f"{id}"}
    finally:
        if cur and cur != None:
            cur.close()
        if con and con != None:
            con.commit()

@api.post("/get_vacation")
def get_vacation(request, id: int):
    try:
        if id < 1:
            raise ValueError("Invalid id")
        data = query_db(f"SELECT v.position, v.salary, v.fleet, v.start_at, v.contract_duration, v.company_email, v.requierments, v.fleet_construct_year, v.fleet_dwt, v.fleet_gd, v.fleet_power, DATE_FORMAT(v.post_date, '%d.%m.%Y') as post_date, v.english_level, v.nationality, v.id, c.logo_path as company_logo_path, c.name as company_name, c.country as company_country FROM vacations v INNER JOIN companies c on v.company_email = c.email WHERE v.id={id}", one=True)
        data["company"] = {
                                "name": data["company_name"], 
                                "logo_path": data["company_logo_path"], 
                                "country": data["company_country"],
                                "email": data["company_email"]
                            }
        del data["company_name"]
        del data["company_logo_path"]
        del data["company_country"]
        del data["company_email"]
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": data}

@api.post("/update_profile_company", auth=AuthBearer())
def update_profile_company(request, email: str, password: str, website: str, mobile_phone: str, country: str, city: str, address: str):
    con = None
    cur = None
    try:
        if request.auth["owner_type"] != "company":
            raise ValueError("Only company user can update company profile")
        if not mobile_phone or not validate_mobile_phone(mobile_phone):
            print(mobile_phone)
            raise ValueError("Invalid phone number")
        if password.strip() and password.__len__() < 4:
            raise ValueError("Password must contain at least 4 chars")
        elif password.strip():
            (hash, salt) = generate_password_hash_and_salt(password)
            password_query = f", password='{hash}', salt='{salt}'"
        else:
            password_query = f""
            
        if not email or not validate_email(email):
            raise ValueError("Invalid email")
        if not country:
            raise ValueError("Country must be set")
        if not city:
            raise ValueError("City must be set")
        if not address:
            raise ValueError("Address must be set")
        if request.auth["owner"] != email and (query_db(f"SELECT email FROM companies WHERE email='{email}' LIMIT 1", one=True) or query_db(f"SELECT email FROM users WHERE email='{email}' LIMIT 1", one=True)):
            raise ValueError("Email already exists")
        phone = mobile_phone
        con = db()
        cur = con.cursor()
        old_email = request.auth["owner"]
        cur.execute(f"UPDATE companies SET email='{email}'{password_query}, website='{website}', mobile_phone='{phone}', email='{email}', country='{country}', city='{city}', address='{address}' WHERE email='{old_email}' LIMIT 1")
        cur.execute(f"UPDATE tokens SET owner='{email}' WHERE owner='{old_email}'")
        cur.execute(f"UPDATE files SET owner='{email}' WHERE owner='{old_email}'")
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": "None"}
    finally:
        if cur and cur != None:
            cur.close()
        if con and con != None:
            con.commit()

@api.post("/update_profile_sailor", auth=AuthBearer())
def update_profile_sailor(request, name: str, password: str, birthday_date: str, mobile_phone: str, position: str, email: str):
    cursor = None
    connection = None
    try :
        if request.auth["owner_type"] != "user":
            raise ValueError("Only sailor can update user profile")
        if not mobile_phone or not validate_mobile_phone(mobile_phone):
            raise ValueError("Invalid phone number")
        if password.strip() and password.__len__() < 4:
            raise ValueError("Password must contain at least 4 chars")
        elif password.strip():
            (hash, salt) = generate_password_hash_and_salt(password)
            password_query = f", password='{hash}', salt='{salt}'"
        else:
            password_query = f""
        if not birthday_date:
            raise ValueError("Birthday date must be set")
        birthday_date = datetime.strptime(birthday_date, "%d.%m.%Y")
        birthday_date = "{Y}-{m}-{d}".format(Y=birthday_date.year, m=birthday_date.month, d=birthday_date.day)
        if not position:
            raise ValueError("Position must be set")
        name = name.strip()
        if not name or name.count(' ') < 1 or name.count(' ') > 5:
            raise ValueError("Name must be set" if not name else "Name field must contain name and surname")
        if request.auth["owner"] != email and (query_db(f"SELECT email FROM companies WHERE email='{email}' LIMIT 1", one=True) or query_db(f"SELECT email FROM users WHERE email='{email}' LIMIT 1", one=True)):
            raise ValueError("Email already exists")
        phone = mobile_phone
        old_email = request.auth["owner"]
        try:
            connection = db()
            cursor = connection.cursor()
            id = cursor.execute(f"UPDATE users SET name='{name}'{password_query}, birthday_date='{birthday_date}', mobile_phone='{phone}', position='{position}' WHERE email='{old_email}' LIMIT 1", ())
            cursor.execute(f"UPDATE tokens SET owner='{email}' WHERE owner='{old_email}'")
            cursor.execute(f"UPDATE files SET owner='{email}' WHERE owner='{old_email}'")
            connection.commit()
            cursor.close()
        except mariadb.Error as e:
            raise Exception("User with such email already exist")
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": f"{id}"}
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.commit()

sort_dict = {"creation": "v.post_date DESC", "start_at_asc": "v.start_at ASC", "start_at_desc": "v.start_at DESC"}
@api.get("/get_vacations")
def get_vacations(request, position = " ", fleet = " ", countries = " ", salary_from = 0, start_at = " ", end_at = " ", sort = " ", offset = 0, limit = settings.MAX_VACATIONS_DISPLAYED):
    try:
        position = position.strip().lower()
        fleet = fleet.strip()
        countries = countries.strip()
        start_at = start_at.strip()
        end_at = end_at.strip()
        sort = sort.strip()
        try:
            pass
            # if start_at:
            #     start_at = datetime.strptime(start_at, "%d.%m.%Y")
            #     start_at = "{Y}-{m}-{d}".format(Y=start_at.year, m=start_at.month, d=start_at.day)
        except:
            start_at = ""
        try:
            pass
            # if end_at:
            #     end_at = datetime.strptime(end_at, "%d.%m.%Y")
            #     end_at = "{Y}-{m}-{d}".format(Y=end_at.year, m=end_at.month, d=end_at.day)
        except:
            end_at = ''
        where_position = ""
        print(position.count(","))
        if len(position) > 0:
            print("A")
            where_position += "("
            for i in range(0, position.count(",") + 1):
                pos = position.split(",")[i]
                print(f"i {i} pos {pos}")
                where_position += f"v.position='{pos}'"
                if i < position.count(','):
                    where_position += " OR "
            where_position += ")"
        if len(fleet) > 0:
            if len(where_position) > 0:
                where_position += " AND "
            print("A")
            where_position += "("
            for i in range(0, fleet.count(",") + 1):
                fl = fleet.split(",")[i]
                print(f"i {i} fleet {fl}")
                where_position += f"v.fleet='{fl}'"
                if i < fleet.count(","):
                    where_position += " OR "
            where_position += ")"

        if len(countries) > 0:
            if len(where_position) > 0:
                where_position += " AND "
            print("A")
            where_position += "("
            for i in range(0, countries.count(",") + 1):
                fl = countries.split(",")[i]
                print(f"i {i} country {fl}")
                where_position += f"c.country='{fl}'"
                if i < countries.count(","):
                    where_position += " OR "
            where_position += ")"
        
        # if salary_from > 0:
        #     if len(where_position) > 0:
        #         where_position += " AND "
        #     where_position += f"v.salary >= {salary_from}"
        
        # if start_at:
        #     if len(where_position) > 0:
        #         where_position += " AND "
        #     where_position += f"v.start_at >= '{start_at}'"
        # if end_at:
        #     if len(where_position) > 0:
        #         where_position += " AND "
        #     where_position += f"v.start_at <= '{end_at}'"
        
        if sort:
            try:
                order_by = "ORDER BY {}".format(sort_dict[sort])
            except:
                order_by = ""
        else:
            order_by = ""
        
        if where_position:
            where_position = f"WHERE {where_position} AND post_date between date_sub(now(), INTERVAL 1 WEEK) and now()"
        else:
            where_position = f"WHERE post_date between date_sub(now(), INTERVAL 1 WEEK) and now()"

        if limit > settings.MAX_VACATIONS_DISPLAYED or limit < 0:
            limit = settings.MAX_VACATIONS_DISPLAYED
        if offset < 0:
            offset = 0
        q = f"SELECT DATE_FORMAT(v.post_date, '%d.%m.%Y %H:%i:%s') as post_date, v.position, v.salary, v.fleet, v.start_at, v.company_email, v.contract_duration, v.id, c.logo_path as company_logo_path, c.name as company_name, c.country as company_contry FROM vacations v INNER JOIN companies c on v.company_email = c.email {where_position} {order_by} LIMIT {limit} OFFSET {offset}"
        print(q)
        data = query_db(q)
        for i in range(0, len(data)):
            data[i]["company"] = {
                                    "name": data[i]["company_name"], 
                                    "logo_path": data[i]["company_logo_path"], 
                                    "contry": data[i]["company_contry"],
                                    "email": data[i]["company_email"]
                                }
            del data[i]["company_name"]
            del data[i]["company_logo_path"]
            del data[i]["company_contry"]
            del data[i]["company_email"]
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": data}

@api.post("/respond_vacation_anonymous")
def respond_vacation_anonymous(request, name: str, surname: str, birthday_date: str, email: str, mobile_phone: str, vacation_id: int):
    try:
        if not request.FILES["cv"]:
            raise ValueError("File not found. Try to send it using multipart form data with name 'cv'")
        if not mobile_phone or not validate_mobile_phone(mobile_phone):
            raise ValueError("Invalid phone number")
        if not birthday_date:
            raise ValueError("Birthday date must be set")
        try:
            birthday_date = datetime.strptime(birthday_date, "%d.%m.%Y")
        except Exception as e:
            raise ValueError("Invalid birth date, it does not match format '%d.%m.%Y'")
        if not name:
            raise ValueError("Name must be set")
        if not surname:
            raise ValueError("Surname must be set")
        if not email or not validate_email(email):
            raise ValueError("Invalid email")
        phone = mobile_phone
        age = calculate_age(birthday_date)
        vacation = get_vacation(None, vacation_id)["extra"]
        msg = '<style>th, td { padding:15px 60px;font-size:30px; } table{ margin: 0px 25%; } div{ padding: 30px; text-align: center; background: #00246A; color: white; font-size: 30px;} body { padding: 0px; } * { margin: 0px; } </style> <div style="padding: 30px;  text-align: center;  background: #00246A;  color: white;  font-size: 30px;"><h1>New responce</h1></div><table><tr><td>Name:</td><td>' + name + ' ' + surname + '</td></tr><tr><td>Age:</td><td>' + f"{age}" + '</td></tr><tr><td>Position:</td><td>' + vacation["position"] +'</td></tr><tr><td>Email:</td><td>' + email + '</td></tr><tr><td>Mobile phone:</td><td>' + phone + '</td></table>'
        sendMail(Mailto(addr=vacation["company"]["email"], name=vacation["company"]["name"]), "CV Responce", msg, request.FILES["cv"].file.read(), filename=request.FILES["cv"].name)
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": "0"}

@api.post("/respond_vacation", auth=AuthBearer())
def respond_vacation(request, vacation_id: int):
    try:
        if request.auth["owner_type"] != "user":
            raise ValueError("Only sailor can respond on vacation")
        email = request.auth["owner"]
        cv_filename = _get_user_cv_filename(email)
        path_to_cv = os.path.join(settings.CV_ROOT, cv_filename)
        fo = open(path_to_cv, "rb")
        filecontent = fo.read()
        userdata = query_db(f"SELECT name, birthday_date, mobile_phone, position FROM users WHERE email='{email}' LIMIT 1", one=True)
        age = calculate_age(userdata["birthday_date"])
        phone = userdata["mobile_phone"]
        vacation = get_vacation(None, vacation_id)["extra"]
        msg = '<style>th, td { padding:15px 60px;font-size:30px; } table{ margin: 0px 25%; } div{ padding: 30px; text-align: center; background: #00246A; color: white; font-size: 30px;} body { padding: 0px; } * { margin: 0px; } </style> <div style="padding: 30px;  text-align: center;  background: #00246A;  color: white;  font-size: 30px;"><h1>New responce</h1></div><table><tr><td>Name:</td><td>' + userdata["name"] + '</td></tr><tr><td>Age:</td><td>' + f"{age}" + '</td></tr><tr><td>Position:</td><td>' + vacation["position"] +'</td></tr><tr><td>Email:</td><td>' + email + '</td></tr><tr><td>Mobile phone:</td><td>' + phone + '</td></tr><tr><td>CV file</td><td><a href="http://' + request.get_host() + f"/api/get_cv?filename={cv_filename}" + '">' + "cv." + cv_filename.split(".")[1] + '</a></td></tr></table>'
        sendMail(Mailto(addr=vacation["company"]["email"], name=vacation["company"]["name"]), "CV Responce", msg, filecontent=filecontent, filename=cv_filename)
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "exntra": "0"}

def sendMail(mailto: Mailto, subject: str, body: str, filecontent = None, filename: str = "cv"):
    pseudonim = settings.MAIL_NAME
    if filecontent:
        if "." in filename:
            ext = filename.split(".")[1]
            filename = filename.split(".")[0]
        else:
            ext = f"{filecontent}".split(".")[1]
        encodedcontent = base64.b64encode(filecontent)
        marker = "AUNIQUEMARKER"
        # Define the main headers.
        part1 = """From: %s <%s>
To: %s <%s>
Subject: %s
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary=%s
--%s
""" % (pseudonim, settings.MAIL_ADDR, mailto.name, mailto.addr, subject, marker, marker)

    # Define the message action
        part2 = """Content-Type: text/html
Content-Transfer-Encoding:8bit

%s
--%s
""" % (body,marker)

    # Define the attachment section
        part3 = """Content-Type: multipart/mixed; name=\"%s\"
Content-Transfer-Encoding:base64
Content-Disposition: attachment; filename=%s

%s
--%s--
""" %(f"{filename}.{ext}", f"{filename}.{ext}", f"{encodedcontent}".split("'")[1], marker)
        message = part1 + part2 + part3
        s = None
    else:
        message = """From: %s <%s>
To: %s <%s>
Subject: %s
Content-Type: text/html
Content-Transfer-Encoding:8bit

%s
""" % (pseudonim, settings.MAIL_ADDR, mailto.name, mailto.addr, subject, body)
    try:
        s = smtplib.SMTP('smtp.gmail.com', 587)
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(settings.MAIL_ADDR, settings.MAIL_PASS)
        s.sendmail(settings.MAIL_ADDR, mailto.addr, f"{message}".encode(settings.ENCODING))
        print(f"Sent message {message} to {mailto}")
    except Exception as e:
        print(e)
        raise Exception("Failed to send message")
    finally:
        if s:
            s.quit()

def get_file(file_path: str):
    if os.path.exists(file_path):
        kind = filetype.guess(file_path)
        if kind is None:
            print(f"Cannot guess file type {file_path}")
            raise Http404
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type=kind)
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
            return response
    raise Http404

@api.get("/get_cv", auth=AuthBearer())
def get_cv(request, filename: str):
    file_path = os.path.join(settings.CV_ROOT, filename)
    return get_file(file_path)

def _get_user_cv_filename(email: str):
    filename = query_db(f"SELECT name FROM files WHERE owner='{email}' AND owner_type='user' LIMIT 1", one=True)
    if filename:
        return filename["name"]
    else:
        raise ValueError("There is no CV file")


def _get_user_cv(email: str):
    filename = query_db(f"SELECT name FROM files WHERE owner='{email}' AND owner_type='user' LIMIT 1", one=True)
    if not filename:
        raise Http404
    filename = filename["name"]
    file_path = os.path.join(settings.CV_ROOT, filename)
    return get_file(file_path)

@api.get("/get_user_cv", auth=AuthBearer())
def get_user_cv(request, email: str):
    if request.auth["owner_type"] != "company":
        raise PermissionDenied
    return _get_user_cv(email)

@api.get("/get_logo")
def get_logo(request, filename: str):
    file_path = os.path.join(settings.LOGO_ROOT, filename)
    return get_file(file_path)

@api.get("/get_company_logo")
def get_company_logo(request, email: str):
    filename = query_db(f"SELECT name FROM files WHERE owner='{email}' AND owner_type='company' LIMIT 1", one=True)
    if not filename:
        print("Default logo")
        filename = "default.png"
    else:
        print("Normal logo")
        filename = filename["name"]
    file_path = os.path.join(settings.LOGO_ROOT, filename)
    print(f"filepath {file_path}")
    return get_file(file_path)

@api.get("/is_company_logo_exists")
def is_company_logo_exists(request, email: str):
    name = query_db(f"SELECT name FROM files WHERE owner='{email}' AND owner_type='company' LIMIT 1", one=True)
    if name:
        return True
    else:
        return False


@api.get("/get_reg_requests", auth=AdminAuthBearer())
def get_reg_requests(request, limit = settings.MAX_REG_REQUESTS_DISPLAYED, offset = 0):
    if limit > settings.MAX_REG_REQUESTS_DISPLAYED or limit < 0:
        limit = settings.MAX_REG_REQUESTS_DISPLAYED
    if offset < 0:
        offset = 0
    try:
        return query_db(f"SELECT name, website, mobile_phone, email, country, city, address FROM companies_requests LIMIT {limit} OFFSET {offset}")
    except Exception as e:
        return f"{e}"

@api.post("/apply_reg_request", auth=AdminAuthBearer())
def apply_reg_request(request, email: str):
    cursor = None
    connection = None
    try:
        connection = db()
        cursor = connection.cursor()
        try:
            cursor.execute(f"INSERT INTO companies(name, password, salt, website, mobile_phone, email, country, city, address) SELECT * FROM companies_requests WHERE email='{email}' LIMIT 1", ())
            id = cursor.execute(f"DELETE FROM companies_requests WHERE email='{email}' LIMIT 1", ())
        except mariadb.Error as e:
            if f"{e}".startswith("Duplicate entry"):
                raise ValueError("Company with such email already exist")
            else:
                return HttpResponseServerError()
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": f"{id}"}
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.commit()

@api.post("/deny_reg_request", auth=AdminAuthBearer())
def deny_reg_request(request, email: str):
    cursor = None
    connection = None
    try:
        connection = db()
        cursor = connection.cursor()
        id = cursor.execute(f"DELETE FROM companies_requests WHERE email='{email}' LIMIT 1", ())
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": f"{id}"}
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.commit()


@api.delete("/remove_vacation", auth=AuthBearer())
def remove_vacation(request, id: int):
    cursor = None
    connection = None
    try:
        company_email = request.auth["owner"]
        owner_email = query_db(f"SELECT company_email FROM vacations WHERE id={id}", one=True)["company_email"]
        print(f"company: {company_email}")
        print(f"owner: {owner_email}")
        if company_email != owner_email:
            raise ValueError("You must be a vacation owner")
        connection = db()
        cursor = connection.cursor()
        cursor.execute(f"DELETE FROM vacations WHERE id={id} AND company_email='{company_email}' LIMIT 1", ())
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": f"{id}"}
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.commit()





@api.patch("/update_vacation", auth=AuthBearer())
def update_vacation(request, id: int, position: str = None, salary: str = None, fleet_type: str = None, start_at: str = None, contract_duration: str = None, requierments: str = None, fleet_construct_year: int = None, fleet_dwt: str = None, fleet_gd: str = None, fleet_power: int = None, english_level: str = None, nationality: str = None):
    try:
        if request.auth["owner_type"] != "company":
            raise ValueError("Only company can update vacation")
        query = "UPDATE vacations SET"
        if position != None:
            query += f" position='{position}'"
        if salary != None:
            # if salary <= 0:
            #     raise ValueError("Salary can't be less than 0")
            if "=" in query:
                query += ","
            query += f" salary='{salary}'"
        if fleet_type != None:
            if "=" in query:
                query += ","
            query += f" fleet='{fleet_type}'"
        if start_at != None:
            # start_at = datetime.strptime(start_at, "%d.%m.%Y")
            # start_at = "{Y}-{m}-{d}".format(Y=start_at.year, m=start_at.month, d=start_at.day)
            if "=" in query:
                query += ","
            query += f" start_at='{start_at}'"
        if contract_duration != None:
            # if contract_duration <= 0:
            #     raise ValueError("Contract duration can't be less than 1")
            if "=" in query:
                query += ","
            query += f" contract_duration='{contract_duration}'"
        if requierments != None:
            if "=" in query:
                query += ","
            query += f" requierments='{requierments}'"
        if fleet_construct_year != None:
            if fleet_construct_year < 1500:
                raise ValueError("Bad fleet construct year")
            if "=" in query:
                query += ","
            query += f" fleet_construct_year={fleet_construct_year}"
        if fleet_dwt != None:
            if "=" in query:
                query += ","
            query += f" fleet_dwt='{fleet_dwt}'"
        if fleet_gd != None:
            if "=" in query:
                query += ","
            query += f" fleet_gd='{fleet_gd}'"
        if fleet_power != None:
            if fleet_power <= 0:
                raise ValueError("Fleet power must be grater that 0")
            if "=" in query:
                query += ","
            query += f" fleet_power={fleet_power}"
        if english_level != None:
            if "=" in query:
                query += ","
            query += f" english_level='{english_level}'"
        if nationality != None:
            if "=" in query:
                query += ","
            query += f" nationality='{nationality}'"
        if "=" not in query:
            raise ValueError("Must be at least one parameter to change")
        company_email = request.auth["owner"]
        query += f" WHERE id={id} AND company_email='{company_email}' LIMIT 1"

        cursor = None
        connection = None
        try:
            connection = db()
            cursor = connection.cursor()
            id = cursor.execute(query, ())
        except Exception as e:
            print(f"{e}")
            raise SystemError("Failed to update vacancy")
        finally:
            if cursor and cursor != None:
                cursor.close()
            if connection and connection != None:
                connection.commit()
    except Exception as e:
        return {"err": f"{e}"}
    else:
        return {"result": "ok"}

@api.post("/send_feedback")
def send_feedback(request, name, email, subject, body:str):
    msg = '<style>th, td { padding:15px 60px;font-size:30px; } table{ margin: 0px 25%; } div{ padding: 30px; text-align: center; background: #00246A; color: white; font-size: 30px;} body { padding: 0px; } * { margin: 0px; } </style> <div style="padding: 30px;  text-align: center;  background: #00246A;  color: white;  font-size: 30px;"><h1>New feedback</h1></div><table><tr><td>Name:</td><td>' + name + '</td></tr><tr><td>Email:</td><td>' + email + '</td></tr><tr><td>Subject:</td><td>' + subject +'</td></tr><tr><td>Body:</td><td>' + body + '</td></tr></table>'
    sendMail(Mailto(addr="info@crewmarine.eu", name=""), "Feedback", msg)


@api.get("/get_company_vacancies")
def get_company_vacancies(request, company_email: str, limit: int = settings.MAX_VACATIONS_DISPLAYED):
    try:
        if limit < 0 or limit > settings.MAX_VACATIONS_DISPLAYED:
            limit = settings.MAX_VACATIONS_DISPLAYED
        q = f"SELECT DATE_FORMAT(v.post_date, '%d.%m.%Y %H:%i:%s') as post_date, v.position, v.salary, v.fleet, v.start_at, v.company_email, v.contract_duration, v.id, c.logo_path as company_logo_path, c.name as company_name, c.country as company_contry FROM vacations v INNER JOIN companies c on v.company_email = c.email WHERE company_email='{company_email}' LIMIT {limit}"
        print(q)
        data = query_db(q)
        for i in range(0, len(data)):
            data[i]["company"] = {
                                    "name": data[i]["company_name"], 
                                    "logo_path": data[i]["company_logo_path"], 
                                    "contry": data[i]["company_contry"],
                                    "email": data[i]["company_email"]
                                }
            del data[i]["company_name"]
            del data[i]["company_logo_path"]
            del data[i]["company_contry"]
            del data[i]["company_email"]
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": data}

@api.get("/request_reset_password")
def req_reset_password(request, email: str):
    cur = None
    connection = None
    try:
        if not email or not validate_email(email):
            raise ValueError("Email invalid")

        info = query_db(f"SELECT * FROM ((SELECT email, 'user' as 'type' FROM users) UNION (SELECT email, 'company' FROM companies)) AS U WHERE U.email='{email}' LIMIT 1", one=True)
        if not info:
            raise ValueError('No such company')
        print(info)
        t = info['type']
        print(t)

        token = secrets.token_hex(256)
        connection = db()
        cur = connection.cursor()
        expire_at = datetime.now() + timedelta(1)
        
        q = f"INSERT INTO tokens (owner_type, owner, token, expire_at) VALUES ('{t}', '{email}', '{token}', '{expire_at}')"
        print(q)
        cur.execute(q, ())
        url = settings.PASSWORD_RESET_URL
        sendMail(Mailto(addr=email, name=""), "Reset password", f'<a href="{url}?token={token}">Click to reset password</a>')
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok"}
    finally:
        if cur and cur != None:
            cur.close()
        if connection and connection != None:
            connection.commit()


@api.get("/reset_password", auth=AuthBearer())
def reset_password(request, password: str):
    cur = None
    connection = None
    try:
        email = request.auth['owner']
        tupl = generate_password_hash_and_salt(password)
        hash = tupl[0]
        salt = tupl[1]
        
        if request.auth["owner_type"] != "company":
            table = 'users'
        else:
            table = 'companies'
        q = f"UPDATE {table} SET salt='{salt}', password='{hash}' WHERE email='{email}' LIMIT 1"
        connection = db()
        cur = connection.cursor()
        cur.execute(q, ())
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok"}
    finally:
        if cur and cur != None:
            cur.close()
        if connection and connection != None:
            connection.commit()


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls)
]


def calculate_age(born):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def validate_mobile_phone(phone):
    reg = '^[0-9+][0-9]*[0-9]$'
    return re.match(reg, phone)

def get_random_salt():
    ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    chars=[]
    for i in range(16):
        chars.append(random.choice(ALPHABET))
    return "".join(chars)

def encode_password(password: str, salt: str):
    return hashlib.sha512((salt + password + salt).encode('utf-8')).hexdigest()

def verify_password(password: str, hash: str, salt: str):
    return encode_password(password, salt) == hash

def generate_password_hash_and_salt(password: str):
    salt = get_random_salt()
    return (encode_password(password, salt), salt)
