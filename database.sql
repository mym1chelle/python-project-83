CREATE TABLE IF NOT EXISTS urls (
        id serial PRIMARY KEY,
        name varchar UNIQUE,
        created_at date);

CREATE TABLE IF NOT EXISTS url_checks (
        id serial PRIMARY KEY,
        url_id bigint REFERENCES urls (id) ON DELETE CASCADE,
        status_code integer,
        h1 varchar,
        title varchar,
        description text,
        created_at date
        );