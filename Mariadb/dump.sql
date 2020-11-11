CREATE TABLE users (
  name TEXT NOT NULL,
  password VARCHAR(1024) NOT NULL,
  salt VARCHAR(32) NOT NULL,
  email VARCHAR(200) PRIMARY KEY,
  birthday_date DATE NOT NULL,
  mobile_phone TEXT NOT NULL,
  position TEXT NOT NULL
);

CREATE TABLE companies (
  name VARCHAR(400) NOT NULL,
  password VARCHAR(1024) NOT NULL,
  salt VARCHAR(32) NOT NULL,
  website VARCHAR(400) DEFAULT '',
  mobile_phone TEXT NOT NULL,
  email VARCHAR(200) PRIMARY KEY,
  country VARCHAR(400) NOT NULL,
  city VARCHAR(400) NOT NULL,
  address VARCHAR(400) NOT NULL,
  logo_path VARCHAR(200) DEFAULT NULL
);

CREATE TABLE companies_requests (
  name VARCHAR(400) NOT NULL,
  password VARCHAR(1024) NOT NULL,
  salt VARCHAR(32) NOT NULL,
  website VARCHAR(400) DEFAULT '',
  mobile_phone TEXT NOT NULL,
  email VARCHAR(200) PRIMARY KEY,
  country VARCHAR(400) NOT NULL,
  city VARCHAR(400) NOT NULL,
  address VARCHAR(400) NOT NULL
);

CREATE TABLE vacations (
  position VARCHAR(400),
  salary TEXT NOT NULL,
  fleet TEXT NOT NULL,
  start_at TEXT NOT NULL,
  contract_duration TEXT NOT NULL,
  company_email VARCHAR(200) NOT NULL,
  requierments VARCHAR(1024) DEFAULT ' ',
  fleet_construct_year INT NOT NULL,
  fleet_dwt VARCHAR(200) NOT NULL,  
  fleet_gd VARCHAR(200) NOT NULL,
  fleet_power INT NOT NULL,
  post_date DATETIME NOT NULL,
  english_level ENUM('Not required', 'Elementary(A1)', 'Pre Intermediate(A2)', 'Intermediate(B1)', 'Upper Intermediate(B2)', 'Advanced(C1)') NOT NULL,
  nationality TEXT NOT NULL,
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

CREATE UNIQUE INDEX companies_email ON companies(email);
CREATE UNIQUE INDEX users_email ON users(email);
CREATE UNIQUE INDEX token ON tokens(token);
CREATE UNIQUE INDEX files_name ON files(name);

-- Password is 1234
-- TODO: change
INSERT INTO companies(name, password, salt, website, mobile_phone, email, country, city, address) VALUES ('Crewmarine', '5da37d7dbe98e16b5207813ced7da51d5025e200a5c3ca4ea966a4bac02c62d1ac8cff8028bdd6054bfb5ab0b67033e66fcb6a6bb487e8a0e10f31a9bf78c105', 'h78FjKOHydIoKRDS', '', '', 'admin@admin.admin', '', '', '') LIMIT 1;