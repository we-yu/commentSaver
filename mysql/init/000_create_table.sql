DROP DATABASE nico_db;
CREATE DATABASE IF NOT EXISTS nico_db;
USE nico_db;

-- TABLE定義

CREATE TABLE IF NOT EXISTS titles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS scrape_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(255) NOT NULL,
    config_type VARCHAR(255) NOT NULL,
    value VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS article_list (
    id INT AUTO_INCREMENT PRIMARY KEY,
    article_id INT UNIQUE,
    title VARCHAR(255) NOT NULL,
    url VARCHAR(255) NOT NULL,
    last_res_id INT,
    moved BOOLEAN,
    new_article_title VARCHAR(1023)
);

CREATE TABLE IF NOT EXISTS article_detail (
    article_id INT NOT NULL,
    resno INT NOT NULL,
    post_name VARCHAR(255),
    post_date DATETIME,
    user_id VARCHAR(255),
    bodytext TEXT,
    page_url VARCHAR(255),
    deleted BOOLEAN,
    PRIMARY KEY (article_id, resno),
    FOREIGN KEY (article_id) REFERENCES article_list(article_id)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS websites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(255) NOT NULL,
    sub_tag1 VARCHAR(255),
    sub_tag2 VARCHAR(255),
    sub_tag3 VARCHAR(255)
);
