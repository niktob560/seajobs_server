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
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI
from ninja.security import HttpBearer

import mariadb

# input validity
import phonenumbers
from validate_email import validate_email
from datetime import datetime, timedelta, date

import hashlib
import time
import random
import secrets

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

db_name = "seajobs"
db_user = "root"
db_password = "QKh8RrWnc51CNcs2DigDsTIxg9J1SXZo"
mail_addr = "seajobs.development@gmail.com"
mail_pass = "Kpl5xKpdzPaHnQ1y"
encoding = "utf-8"
images_path = "/tmp/"
cv_path = "/tmp/"

def db():
    return mariadb.connect(
        user=db_user,
        password=db_password,
        host="128.0.129.115",
        port=3308,
        database=db_name)

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
            connection = db()
            cursor = connection.cursor()
            id = cursor.execute("INSERT INTO users(name, password, email, birthday_date, mobile_phone, position) VALUES (?, ?, ?, ?, ?, ?) LIMIT 1", (name, password, email, birthday_date, phone, position))
            connection.commit()
            cursor.close()
        except mariadb.Error as e:
            raise Exception("User with such email already exist")
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
            connection = db()
            cursor = connection.cursor()
            id = cursor.execute("INSERT INTO companies(name, password, website, mobile_phone, email, country, city, address) VALUES (?, ?, ?, ?, ?, ?, ?, ?) LIMIT 1", (company_name, password, website, phone, email, country, city, address))
            connection.commit()
            cursor.close()
        except mariadb.Error as e:
            print(e)
            raise Exception("Company with such email already exist")
    except Exception as e:
        return {"result": "err", "extra": "{}".format(e)}
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
        return {"result": "ok", "extra": f"{data}"}

@api.post("/get_profile_user", auth=AuthBearer())
def get_profile_user(request):
    try:
        auth = request.auth
        print(auth)
        if auth["owner_type"] != "user":
            raise ValueError("This is not a user account")
        email = auth["owner"]
        data = query_db(f"SELECT name, email, birthday_date, mobile_phone, position FROM users WHERE email='{email}' LIMIT 1", args=(), one=True)
        print(data)
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": f"{data}"}

def handle_uploaded_file(filename, file):
    with open(filename, "wb+") as destination:
        for chunk in file.chunks():
            destination.write(chunk)

@api.post("/upload_cv", auth=AuthBearer())
def upload_cv(request):
    try:
        if request.auth["owner_type"] != "user":
            raise ValueError("Only sailor can upload CV")
        file = request.FILES["cv"]
        filename = secrets.token_hex(64)
        ext = f"{file}".split(".")[1]
        filename += f".{ext}"
        path = f"{cv_path}{filename}"
        handle_uploaded_file(path, file)
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": f"{filename}"}

@api.post("/upload_logo", auth=AuthBearer())
def upload_logo(request):
    con = None
    cur = None
    try:
        if request.auth["owner_type"] != "company":
            raise ValueError("Only company can upload logo")
        file = request.FILES["logo"]
        filename = secrets.token_hex(64)
        path = f"{images_path}{filename}"
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
def add_vacation(request, position: str, salary: int, fleet_type: str, start_at: str, end_at: str, nationality: str, english_level: str, requierments: str, fleet_construct_year: int, fleet_dtw: str, fleet_gd_type: str, fleet_power: int):
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
        if not end_at:
            raise ValueError("Bad end date")
        end_at = datetime.strptime(end_at, "%d.%m.%Y")
        end_at = "{Y}-{m}-{d}".format(Y=end_at.year, m=end_at.month, d=end_at.day)
        if not nationality:
            raise ValueError("Bad nationality")
        if not english_level:
            raise ValueError("Bad english level")
        if not requierments:
            raise ValueError("Bad requierments")
        if fleet_construct_year < 1500:
            raise ValueError("Bad fleet construct year")
        if not fleet_dtw:
            raise ValueError("Bad fleet DTW")
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
        id = cur.execute(f"INSERT INTO vacations (position, salary, fleet, start_at, end_at, company_email, post_date, english_level) VALUES('{position}', '{salary}', '{fleet_type}', '{start_at}', '{end_at}', '{company_email}', '{post_date}', '{english_level}') LIMIT 1", ())
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
        data = query_db(f"SELECT v.*, c.logo_path as company_logo_path, c.name as company_name, c.country as company_contry FROM vacations v INNER JOIN companies c on v.company_email = c.email WHERE id='{id}'", one=True)
        data["company"] = {
                                "name": data["company_name"], 
                                "logo_path": data["company_logo_path"], 
                                "contry": data["company_contry"],
                                "email": data["company_email"]
                            }
        del data["company_name"]
        del data["company_logo_path"]
        del data["company_contry"]
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
        if not password or password.__len__() < 4:
            raise ValueError("Password must contain at least 4 chars")
        if not email or not validate_email(email):
            raise ValueError("Invalid email")
        if not country:
            raise ValueError("Country must be set")
        if not city:
            raise ValueError("City must be set")
        if not address:
            raise ValueError("Address must be set")
        if query_db(f"SELECT email FROM companies WHERE email='{email}' LIMIT 1", one=True) or query_db(f"SELECT email FROM users WHERE email='{email}' LIMIT 1", one=True):
            raise ValueError("Email already exists")
        phone = "+{}{}".format(mobile_phone.country_code, mobile_phone.national_number)
        con = db()
        cur = con.cursor()
        old_email = request.auth["owner"]
        cur.execute(f"UPDATE companies SET email='{email}', password='{password}', website='{website}', mobile_phone='{phone}', email='{email}', country='{country}', city='{city}', address='{address}' WHERE email='{old_email}' LIMIT 1")
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
        if not password or password.__len__() < 4:
            raise ValueError("Password must contain at least 4 chars")
        if not birthday_date:
            raise ValueError("Birthday date must be set")
        birthday_date = datetime.strptime(birthday_date, "%d.%m.%Y")
        birthday_date = "{Y}-{m}-{d}".format(Y=birthday_date.year, m=birthday_date.month, d=birthday_date.day)
        if not position:
            raise ValueError("Position must be set")
        if not name:
            raise ValueError("Name must be set")
        if query_db(f"SELECT email FROM companies WHERE email='{email}' LIMIT 1", one=True) or query_db(f"SELECT email FROM users WHERE email='{email}' LIMIT 1", one=True):
            raise ValueError("Email already exists")
        phone = "+{}{}".format(mobile_phone.country_code, mobile_phone.national_number)
        old_email = request.auth["owner"]
        try:
            connection = db()
            cursor = connection.cursor()
            id = cursor.execute(f"UPDATE users SET name='{name}', password='{password}', birthday_date='{birthday_date}', mobile_phone='{phone}', position='{position}' WHERE email='{old_email}' LIMIT 1", ())
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
def get_vacations(request, position: str, fleet: str, country: str, salary_from: int, start_at: str, end_at: str, sort: str):
    try:
        position = position.strip()
        fleet = fleet.strip()
        country = country.strip()
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
            end_at = ""
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
        
        if salary_from > 0:
            if len(where_position) > 0:
                where_position += " AND "
            where_position += f"v.salary >= {salary_from}"

        if country:
            if len(where_position) > 0:
                where_position += " AND "
            where_position += f"c.country='{country}'"
        
        if start_at:
            if len(where_position) > 0:
                where_position += " AND "
            where_position += f"v.start_at >= '{start_at}'"
        if end_at:
            if len(where_position) > 0:
                where_position += " AND "
            where_position += f"v.end_at <= '{end_at}'"
        
        if sort:
            try:
                order_by = "ORDER BY {}".format(sort_dict[sort])
            except:
                order_by = ""
        else:
            order_by = ""
        
        if where_position:
            where_position = "WHERE {}".format(where_position)
        q = f"SELECT v.*, c.logo_path as company_logo_path, c.name as company_name, c.country as company_contry FROM vacations v INNER JOIN companies c on v.company_email = c.email {where_position} {order_by}"
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

@api.post("/respond_vacation")
def respond_vacation(request, name: str, surname: str, birthday_date: str, email: str, mobile_phone: str, path_to_cv: str, vacation_id: int):
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
        print(vacation)
        msg = '<style>th, td { padding:15px 60px;font-size:30px; } table{ margin: 0px 25%; } div{ padding: 30px; text-align: center; background: #00246A; color: white; font-size: 30px;} body { padding: 0px; } * { margin: 0px; } </style> <div style="padding: 30px;  text-align: center;  background: #00246A;  color: white;  font-size: 30px;"><h1>New responce</h1></div><table><tr><td>Name:</td><td>' + name + ' ' + surname + '</td></tr><tr><td>Age:</td><td>' + f"{age}" + '</td></tr><tr><td>Position:</td><td>' + vacation["position"] +'</td></tr><tr><td>Email:</td><td>' + email + '</td></tr><tr><td>Mobile phone:</td><td>' + phone + '</td></tr><tr><td>CV file</td><td><a href="https://google.com/">' + "cv." + path_to_cv.split(".")[1] + '</a></td></tr></table>'
        sendMail(Mailto(addr=vacation["company"]["email"], name=vacation["company"]["name"]), "CV Responce", msg, f"{cv_path}{path_to_cv}")
    except Exception as e:
        return {"result": "err", "extra": f"{e}"}
    else:
        return {"result": "ok", "extra": "0"}

def sendMail(mailto: Mailto, subject: str, body: str, filename: str):
    fo = open(f"{filename}", "rb")
    filecontent = fo.read()
    encodedcontent = base64.b64encode(filecontent)
    marker = "AUNIQUEMARKER"
    # Define the main headers.
    part1 = """From: Seajobs <%s>
To: %s <%s>
Subject: %s
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary=%s
--%s
""" % (mail_addr, mailto.name, mailto.addr, subject, marker, marker)

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
""" %(filename, filename, f"{encodedcontent}".split("'")[1], marker)
    message = part1 + part2 + part3
    s = smtplib.SMTP('smtp.gmail.com', 587)
    try:
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(mail_addr, mail_pass)
        s.sendmail(mail_addr, mailto.addr, f"{message}".encode(encoding))
        print(f"Sent message {message} to {mailto}")
    except Exception as e:
        print(e)
        raise Exception("Failed to send message")
    finally:
        s.quit()

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls)
]


def calculate_age(born):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))