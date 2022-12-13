from flask import Flask, render_template, request, redirect, flash, url_for
import psycopg2
import validators
from datetime import datetime
import os
import requests
from bs4 import BeautifulSoup


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS urls (
        id serial PRIMARY KEY,
        name varchar UNIQUE,
        created_at date
        );"""
    )

cur.execute(
    """
    CREATE TABLE IF NOT EXISTS url_checks (
        id serial PRIMARY KEY,
        url_id bigint REFERENCES urls (id) ON DELETE CASCADE,
        status_code integer,
        h1 varchar,
        title varchar,
        description text,
        created_at date
        );"""
    )
conn.commit()


with open('database.sql', 'w') as file:
    cur.copy_to(file, 'urls', '|')


@app.route('/')
def index():
    return render_template(
        "start_page.html"
    )


@app.route('/urls', methods=['GET', 'POST'])
def add_url():
    if request.method == 'POST':
        data = request.form.to_dict()
        url = data.get('url')
        if validators.url(url):
            print('True')
            created_at = datetime.now()
            print(created_at)
            cur.execute("SELECT name FROM urls WHERE name=(%s);", (url,))
            get_url = cur.fetchone()
            if get_url is None:
                cur.execute(
                    """
                    INSERT INTO urls (name, created_at)
                    VALUES (%s, %s);""", (url, created_at))
                conn.commit()
                flash('Страница успешно добавлена', 'success')
                with open('database.sql', 'w') as file:
                    cur.copy_to(file, 'urls', '|')
            else:
                flash('Страница уже существует', 'info')
                cur.execute("SELECT id FROM urls WHERE name=(%s);", (url,))
                redirect(f'urls/{cur.fetchone()[0]}')
        else:
            flash('Некорректный URL', 'danger')
            return render_template('start_page.html', url_adress=url)
        cur.execute("SELECT id FROM urls WHERE name=(%s);", (url,))
        return redirect(f'urls/{cur.fetchone()[0]}')
    else:
        cur.execute(
            """
            SELECT *
            FROM (
            SELECT DISTINCT ON(dist_urls.id)
            dist_urls.id, dist_urls.name,
            sorted_checks.status_code, sorted_checks.created_at
            FROM (SELECT * FROM urls ORDER BY created_at DESC) AS dist_urls
            LEFT JOIN (
                SELECT *
                FROM url_checks
                ORDER BY created_at DESC
                ) AS sorted_checks
            ON sorted_checks.url_id = dist_urls.id) as result;
            """
            )
        last_check = [
            ['' if x is None else x for x in row]
            for row in cur.fetchall()]
        return render_template(
            "sites_table.html",
            last_check=last_check,
        )


@app.route('/urls/<id>')
def show_url(id):
    cur.execute("SELECT * FROM urls WHERE id=(%s);", (id,))
    url = cur.fetchall()[0]
    cur.execute(
        """
        SELECT * FROM url_checks
        WHERE url_id=(%s) ORDER BY id DESC;
        """, (id,))
    checks = cur.fetchall()
    return render_template(
        "urls.html",
        url_data=url,
        checks_url=checks
    )


@app.post('/urls/<id>/checks')
def check_url(id):
    created_at = datetime.now()
    cur.execute("SELECT name FROM urls WHERE id=(%s);", (id,))
    url = cur.fetchall()[0][0]
    try:
        title = ''
        h1 = ''
        description = ''
        r = requests.get(url)
        status_code = r.status_code
        html_doc = r.text
        soup = BeautifulSoup(html_doc, 'html.parser')
        if soup.title:
            title = soup.title.string
        if soup.find('h1'):
            h1 = soup.find('h1').string
        if soup.find("meta", {"name": "description"}):
            description = soup.find("meta", {"name": "description"})['content']
        cur.execute(
            """
            INSERT INTO url_checks (
                url_id, status_code, h1, title, description, created_at)
            VALUES (%s, %s, %s, %s, %s, %s);""",
            (id, status_code, h1, title, description, created_at))
        conn.commit()
        with open('database.sql', 'w') as file:
            cur.copy_to(file, 'url_checks', '|')
    except requests.exceptions.ConnectionError:
        flash('Произошла ошибка при проверке', 'danger')
    return redirect(url_for('show_url', id=id))
