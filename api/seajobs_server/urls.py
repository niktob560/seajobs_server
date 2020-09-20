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
import phonenumbers
from validate_email import validate_email
from datetime import datetime, timedelta, date

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
        data = query_db(f"SELECT owner, owner_type FROM tokens WHERE token='{token}' LIMIT 1", (), one=True)
        if data:
            return data

@api.post("/register_sailor")
def register_sailor(request, name: str, password: str, email: str, birthday_date: str, mobile_phone: str, position: str):
    cursor = None
    connection = None
    try :
        mobile_phone = phonenumbers.parse(mobile_phone, "RU")
        if not mobile_phone or mobile_phone == None:
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
        if not name:
            raise ValueError("Name must be set")
        phone = "+{}{}".format(mobile_phone.country_code, mobile_phone.national_number)
        try:
            if query_db(f"SELECT email FROM companies WHERE email='{email}'"):
                raise Exception("Company with such email already exist")
            connection = db()
            cursor = connection.cursor()
            id = cursor.execute("INSERT INTO users(name, password, email, birthday_date, mobile_phone, position) VALUES (?, ?, ?, ?, ?, ?) LIMIT 1", (name, password, email, birthday_date, phone, position))
            connection.commit()
            cursor.close()
        except mariadb.Error as e:
            print(f"{e}")
            if f"{e}".startswith("Duplicate entry"):
                raise Exception("User with such email already exist")
            else:
                return HttpResponseServerError()
    except Exception as e:
        return {"result": "err", "extra": "{}".format(e)}
    else:
        return {"result": "ok", "extra": f"{id}"}
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.commit()

@api.post("/register_company")
def register_company(request, company_name: str, password: str, website: str, mobile_phone: str, email: str, country: str, city: str, address: str):
    cursor = None
    connection = None
    try :
        mobile_phone = phonenumbers.parse(mobile_phone, "RU")
        if not mobile_phone or mobile_phone == None:
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
        phone = "+{}{}".format(mobile_phone.country_code, mobile_phone.national_number)
        try:
            if query_db(f"SELECT email FROM users WHERE email='{email}'"):
                raise Exception("User with such email already exist")
            connection = db()
            cursor = connection.cursor()
            id = cursor.execute("INSERT INTO companies(name, password, website, mobile_phone, email, country, city, address) VALUES (?, ?, ?, ?, ?, ?, ?, ?) LIMIT 1", (company_name, password, website, phone, email, country, city, address))
            connection.commit()
            cursor.close()
        except mariadb.Error as e:
            print(f"{e}")
            if f"{e}".startswith("Duplicate entry"):
                raise Exception("Company with such email already exist")
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
        user = query_db(f"SELECT * FROM users WHERE email='{email}' AND password='{password}' LIMIT 1", one=True)
        if not user:
            company = query_db(f"SELECT * FROM companies WHERE email='{email}' AND password='{password}' LIMIT 1", one=True)
            if not company:
                raise ValueError("Invalid credentails")
            else:
                type = "company"
        else:
            type = "user"
        token = secrets.token_hex(256)
        connection = db()
        cur = connection.cursor()
        expire_at = datetime.now() + timedelta(1)
        
        q = f"INSERT INTO tokens (owner_type, owner, token, expire_at) VALUES ('{type}', '{email}', '{token}', '{expire_at}') LIMIT 1"
        print(q)
        cur.execute(q, ())
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": { "token": f"{token}", "type": type } }
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
    con = None
    cur = None
    try:
        if request.auth["owner_type"] != "user":
            raise ValueError("Only sailor can upload CV")
        email = request.auth["owner"]
        file = request.FILES["cv"]
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
        return {"result": "ok", "extra": f"{filename}"}
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
        filename = secrets.token_hex(64)
        ext = f"{file}".split(".")[1]
        filename += f".{ext}"
        path = f"{settings.LOGO_ROOT}{filename}"
        handle_uploaded_file(path, file)
        email = request.auth["owner"]
        con = db()
        cur = con.cursor()
        cur.execute(f"UPDATE companies SET logo_path='{filename}' WHERE email='{email}' LIMIT 1", ())
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
def add_vacation(request, position: str, salary: int, fleet_type: str, start_at: str, contract_duration: int, nationality: str, english_level: str, requierments: str, fleet_construct_year: int, fleet_dwt: str, fleet_gd_type: str, fleet_power: int):
    con = None
    cur = None
    try:
        if request.auth["owner_type"] != "company":
            raise ValueError("Only company can add vacation")
        if not position:
            raise ValueError("Bad position")
        if salary < 0:
            raise ValueError("Salary can't be less than 0")
        if not fleet_type:
            raise ValueError("Bad fleet type")
        if not start_at:
            raise ValueError("Bad start date")
        start_at = datetime.strptime(start_at, "%d.%m.%Y")
        start_at = "{Y}-{m}-{d}".format(Y=start_at.year, m=start_at.month, d=start_at.day)
        if contract_duration <= 0:
            raise ValueError("Contract duration can't be less than 1")
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
        print(english_level)
        if english_level.startswith("Не обязателен"):
            print("Changing")
            english_level = "Not required"
        company_email = request.auth["owner"]
        post_date = datetime.now()
        post_date = "{Y}-{m}-{d}".format(Y=post_date.year, m=post_date.month, d=post_date.day)
        con = db()
        cur = con.cursor()
        id = cur.execute(f"INSERT INTO vacations (position, salary, fleet, start_at, contract_duration, company_email, post_date, english_level, nationality, requierments, fleet_construct_year, fleet_dwt, fleet_gd, fleet_power) VALUES('{position}', '{salary}', '{fleet_type}', '{start_at}', '{contract_duration}', '{company_email}', '{post_date}', '{english_level}', '{nationality}', '{requierments}', '{fleet_construct_year}', '{fleet_dwt}', '{fleet_gd_type}', '{fleet_power}')", ())
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
        data = query_db(f"SELECT v.position, v.salary, v.fleet, DATE_FORMAT(v.start_at, '%d.%m.%Y') as start_at, v.contract_duration, v.company_email, v.requierments, v.fleet_construct_year, v.fleet_dwt, v.fleet_gd, v.fleet_power, DATE_FORMAT(v.post_date, '%d.%m.%Y') as post_date, v.english_level, v.nationality, v.id, c.logo_path as company_logo_path, c.name as company_name, c.country as company_country FROM vacations v INNER JOIN companies c on v.company_email = c.email WHERE v.id={id}", one=True)
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
        mobile_phone = phonenumbers.parse(mobile_phone, "RU")
        if not mobile_phone or mobile_phone == None:
            raise ValueError("Invalid phone number")
        if password and password.__len__() < 4:
            raise ValueError("Password must contain at least 4 chars")
        elif password.strip():
            password_query = f", password='{password}'"
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
        phone = "+{}{}".format(mobile_phone.country_code, mobile_phone.national_number)
        con = db()
        cur = con.cursor()
        old_email = request.auth["owner"]
        cur.execute(f"UPDATE companies SET email='{email}'{password_query}, website='{website}', mobile_phone='{phone}', email='{email}', country='{country}', city='{city}', address='{address}' WHERE email='{old_email}' LIMIT 1")
        cur.execute(f"UPDATE tokens SET owner='{email}' WHERE owner='{old_email}' LIMIT 1")
        cur.execute(f"UPDATE files SET owner='{email}' WHERE owner='{old_email}' LIMIT 1")
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
        mobile_phone = phonenumbers.parse(mobile_phone, "RU")
        if not mobile_phone or mobile_phone == None:
            raise ValueError("Invalid phone number")
        if password and password.__len__() < 4:
            raise ValueError("Password must contain at least 4 chars")
        elif password.strip():
            password_query = f", password='{password}'"
        else:
            password_query = f""
        if not birthday_date:
            raise ValueError("Birthday date must be set")
        birthday_date = datetime.strptime(birthday_date, "%d.%m.%Y")
        birthday_date = "{Y}-{m}-{d}".format(Y=birthday_date.year, m=birthday_date.month, d=birthday_date.day)
        if not position:
            raise ValueError("Position must be set")
        if not name:
            raise ValueError("Name must be set")
        if request.auth["owner"] != email and (query_db(f"SELECT email FROM companies WHERE email='{email}' LIMIT 1", one=True) or query_db(f"SELECT email FROM users WHERE email='{email}' LIMIT 1", one=True)):
            raise ValueError("Email already exists")
        phone = "+{}{}".format(mobile_phone.country_code, mobile_phone.national_number)
        old_email = request.auth["owner"]
        try:
            connection = db()
            cursor = connection.cursor()
            id = cursor.execute(f"UPDATE users SET name='{name}'{password_query}, birthday_date='{birthday_date}', mobile_phone='{phone}', position='{position}' WHERE email='{old_email}' LIMIT 1", ())
            cursor.execute(f"UPDATE tokens SET owner='{email}' WHERE owner='{old_email}' LIMIT 1")
            cursor.execute(f"UPDATE files SET owner='{email}' WHERE owner='{old_email}' LIMIT 1")
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

sort_dict = {"creation": "v.post_date", "start_at_asc": "v.start_at ASC", "start_at_desc": "v.start_at DESC"}
@api.post("/get_vacations")
def get_vacations(request, position: str, fleet: str, countries: str, salary_from: int, start_at: str, end_at: str, sort: str):
    try:
        position = position.strip()
        fleet = fleet.strip()
        countries = countries.strip()
        start_at = start_at.strip()
        end_at = end_at.strip()
        sort = sort.strip()
        try:
            if start_at:
                start_at = datetime.strptime(start_at, "%d.%m.%Y")
                start_at = "{Y}-{m}-{d}".format(Y=start_at.year, m=start_at.month, d=start_at.day)
        except:
            start_at = ""
        try:
            if end_at:
                end_at = datetime.strptime(end_at, "%d.%m.%Y")
                end_at = "{Y}-{m}-{d}".format(Y=end_at.year, m=end_at.month, d=end_at.day)
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
        
        if salary_from > 0:
            if len(where_position) > 0:
                where_position += " AND "
            where_position += f"v.salary >= {salary_from}"
        
        if start_at:
            if len(where_position) > 0:
                where_position += " AND "
            where_position += f"v.start_at >= '{start_at}'"
        if end_at:
            if len(where_position) > 0:
                where_position += " AND "
            where_position += f"v.start_at <= '{end_at}'"
        
        if sort:
            try:
                order_by = "ORDER BY {}".format(sort_dict[sort])
            except:
                order_by = ""
        else:
            order_by = ""
        
        if where_position:
            where_position = "WHERE {}".format(where_position)
        limit = settings.MAX_VACATIONS_DISPLAYED
        q = f"SELECT v.position, v.salary, v.fleet, DATE_FORMAT(v.start_at, '%d.%m.%Y') as start_at, v.company_email, v.contract_duration, v.id, c.logo_path as company_logo_path, c.name as company_name, c.country as company_contry FROM vacations v INNER JOIN companies c on v.company_email = c.email {where_position} {order_by} LIMIT {limit}"
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
        mobile_phone = phonenumbers.parse(mobile_phone, "RU")
        if not mobile_phone or mobile_phone == None:
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
        phone = "+{}{}".format(mobile_phone.country_code, mobile_phone.national_number)
        age = calculate_age(birthday_date)
        vacation = get_vacation(None, vacation_id)["extra"]
        msg = '<style>th, td { padding:15px 60px;font-size:30px; } table{ margin: 0px 25%; } div{ padding: 30px; text-align: center; background: #00246A; color: white; font-size: 30px;} body { padding: 0px; } * { margin: 0px; } </style> <div style="padding: 30px;  text-align: center;  background: #00246A;  color: white;  font-size: 30px;"><h1>New responce</h1></div><table><tr><td>Name:</td><td>' + name + ' ' + surname + '</td></tr><tr><td>Age:</td><td>' + f"{age}" + '</td></tr><tr><td>Position:</td><td>' + vacation["position"] +'</td></tr><tr><td>Email:</td><td>' + email + '</td></tr><tr><td>Mobile phone:</td><td>' + phone + '</td></table>'
        sendMail(Mailto(addr=vacation["company"]["email"], name=vacation["company"]["name"]), "CV Responce", msg, request.FILES["cv"].file.read(), filename=request.FILES["cv"].named)
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
        name = userdata["name"].split(" ")[0]
        surname = userdata["name"].split(" ")[1]
        age = calculate_age(userdata["birthday_date"])
        phone = userdata["mobile_phone"]
        vacation = get_vacation(None, vacation_id)["extra"]
        msg = '<style>th, td { padding:15px 60px;font-size:30px; } table{ margin: 0px 25%; } div{ padding: 30px; text-align: center; background: #00246A; color: white; font-size: 30px;} body { padding: 0px; } * { margin: 0px; } </style> <div style="padding: 30px;  text-align: center;  background: #00246A;  color: white;  font-size: 30px;"><h1>New responce</h1></div><table><tr><td>Name:</td><td>' + name + ' ' + surname + '</td></tr><tr><td>Age:</td><td>' + f"{age}" + '</td></tr><tr><td>Position:</td><td>' + vacation["position"] +'</td></tr><tr><td>Email:</td><td>' + email + '</td></tr><tr><td>Mobile phone:</td><td>' + phone + '</td></tr><tr><td>CV file</td><td><a href="http://' + request.get_host() + f"/api/get_cv?filename={cv_filename}" + '">' + "cv." + cv_filename.split(".")[1] + '</a></td></tr></table>'
        sendMail(Mailto(addr=vacation["company"]["email"], name=vacation["company"]["name"]), "CV Responce", msg, filecontent, filename=cv_filename)
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "exntra": "0"}

def sendMail(mailto: Mailto, subject: str, body: str, filecontent, filename: str = "cv"):
    if "." in filename:
        ext = filename.split(".")[1]
        filename = filename.split(".")[0]
    else:
        ext = f"{filecontent}".split(".")[1]
    encodedcontent = base64.b64encode(filecontent)
    marker = "AUNIQUEMARKER"
    # Define the main headers.
    part1 = """From: Seajobs <%s>
To: %s <%s>
Subject: %s
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary=%s
--%s
""" % (settings.MAIL_ADDR, mailto.name, mailto.addr, subject, marker, marker)

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
    s = smtplib.SMTP('smtp.gmail.com', 587)
    try:
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
        return ""


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
        raise Http404
    filename = filename["name"]
    file_path = os.path.join(settings.LOGO_ROOT, filename)
    return get_file(file_path)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls)
]


def calculate_age(born):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))