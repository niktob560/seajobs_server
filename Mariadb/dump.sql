CREATE TABLE users (
  name TEXT NOT NULL,
  password VARCHAR(400) NOT NULL,
  email VARCHAR(200) PRIMARY KEY,
  birthday_date DATE NOT NULL,
  mobile_phone TEXT NOT NULL,
  position TEXT NOT NULL
);

CREATE TABLE companies (
  name VARCHAR(400) NOT NULL,
  password VARCHAR(400) NOT NULL,
  website VARCHAR(400) DEFAULT '',
  mobile_phone TEXT NOT NULL,
  email VARCHAR(200) PRIMARY KEY,
  country VARCHAR(400) NOT NULL,
  city VARCHAR(400) NOT NULL,
  address VARCHAR(400) NOT NULL,
  logo_path VARCHAR(128) DEFAULT NULL
);

CREATE TABLE vacations (
  position VARCHAR(400),
  salary INT UNSIGNED NOT NULL,
  fleet TEXT NOT NULL,
  start_at DATE NOT NULL,
  end_at DATE NOT NULL,
  company_email VARCHAR(200) NOT NULL,
  post_date DATE NOT NULL,
  english_level ENUM('Not required', 'Elementary(A1)', 'Pre Intermediate(A2)', 'Intermediate(B1)', 'Upper Intermediate(B2)', 'Advanced(C1)') NOT NULL,
  nationality NOT NULL,
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  FOREIGN KEY (company_email) REFERENCES companies(email) ON DELETE CASCADE ON UPDATE CASCADE
);


CREATE TABLE tokens (
  owner_type ENUM('user', 'company') NOT NULL,
  owner VARCHAR(200) NOT NULL,
  token VARCHAR(512) PRIMARY KEY UNIQUE,
  expire_at DATETIME NOT NULL
) ENGINE=MEMORY;

CREATE TABLE files (
  owner_type ENUM('user', 'company') NOT NULL,
  owner VARCHAR(200) NOT NULL,
  name VARCHAR(200) PRIMARY KEY
);

CREATE INDEX vacations_salary ON vacations(salary);
CREATE INDEX vacations_post ON vacations(post_date);
CREATE INDEX vacations_start ON vacations(start_at);
CREATE INDEX vacations_end ON vacations(end_at);

CREATE UNIQUE INDEX companies_email ON companies(email);
CREATE UNIQUE INDEX users_email ON users(email);
CREATE UNIQUE INDEX token ON tokens(token);
CREATE UNIQUE INDEX files_name ON files(name);