from flask import Flask, render_template, g, current_app, request
from flask_paginate import Pagination
from sqlite3 import connect
from datetime import datetime
import re
from urllib import parse
from flask_frozen import Freezer
import sys
import configparser

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
config = configparser.ConfigParser()
config.read("config.txt")
FREEZER_DESTINATION = config.get("Configuration", "destination")
PER_PAGE = config.get("Configuration", "per_page")
PER_PAGE = int(PER_PAGE)

app = Flask(__name__)
app.config['FREEZER_DESTINATION'] = FREEZER_DESTINATION
app.config.from_object(__name__)
app.config['FREEZER_RELATIVE_URLS'] = True
freezer = Freezer(app)
extra_bold = re.compile(r"</b>.*?<b>", re.MULTILINE)


# -----------------------------------------------------------------------------
# DATABASE
# -----------------------------------------------------------------------------
def connect_db():
    return connect("anon.db")


@app.before_request
def before_request():
    g.db = connect_db()


@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.db.close()


def query_db(query, args=(), one=False):
    cur = g.db.execute(query, args)
    rv = [dict((cur.description[idx][0], value)
               for idx, value in enumerate(row)) for row in cur.fetchall()]
    return (rv[0] if rv else None) if one else rv
    

def fetch_outlet_url(outlet_name):
    outlet_name = parse.unquote_plus(outlet_name)
    outlet_url = query_db(
        "SELECT url FROM outlets WHERE name = ?",
        (outlet_name,),
        one=True)
    return outlet_url


def fetch_outlet_name(outlet_url):
    outlet_url = parse.unquote_plus(outlet_url)
    outlet_name = query_db(
        "SELECT name FROM outlets WHERE url= ?",
        (outlet_url,),
        one=True)
    return outlet_name


def get_total_anon_pages():
    g.db = connect_db() # Is this necessary? Pass in connection?
    results = query_db("SELECT count(*) FROM anon", '', one=True)
    total=int(next(iter(results.values())))
    num_pages = total/PER_PAGE
    g.db.close()
    return num_pages


def get_total_outlet_pages(outlet):
    g.db = connect_db()
    results = query_db('SELECT count(*) FROM anon where source = ?', (outlet,), one=True)
    total=int(next(iter(results.values())))
    return total


def get_outlet_urls():
    g.db = connect_db()
    urls = query_db("SELECT DISTINCT url FROM outlets ORDER BY url")
    g.db.close()
    return urls


def get_outlet_names():
    g.db = connect_db()
    names = query_db("SELECT DISTINCT name FROM outlets ORDER BY name")
    g.db.close()
    return names


# -----------------------------------------------------------------------------
# TEMPLATE FILTERS
# -----------------------------------------------------------------------------
@app.template_filter('datetimeformat')
def datetimeformat(value, date_format='%B %e, %Y'):
    d = datetime.strptime(value, '%Y-%m-%d')
    return d.strftime(date_format)


@app.template_filter('clean_content')
def clean_content(content):
    content = content.strip()
    content = content.replace('\n', ' ').replace('\r', '')
    content = content.replace('<b>...</b>', '...')
    content = content.replace('<br>', '')
    content = re.sub(extra_bold, "\1 ", content)
    return content


# Makes for prettier URLs
@app.template_filter('plus_for_spaces')
def plus_for_spaces(content):
    content = content.strip()
    content = content.replace(' ', '+')
    return content


# -----------------------------------------------------------------------------
# PAGINATOR FUNCTIONS
# -----------------------------------------------------------------------------
def get_css_framework():
    return current_app.config.get('CSS_FRAMEWORK', 'bootstrap3')


def get_link_size():
    return current_app.config.get('LINK_SIZE', 'sm')


def show_single_page_or_not():
    return current_app.config.get('SHOW_SINGLE_PAGE', False)


def get_page_items():
    page = int(request.args.get('page', 1))
    per_page = request.args.get('per_page')
    if not per_page:
        per_page = PER_PAGE = 50;
    else:
        per_page = int(per_page)
    offset = (page - 1) * per_page
    return page, per_page, offset


def get_pagination(**kwargs):
    kwargs.setdefault('record_name', 'records')
    return Pagination(css_framework=get_css_framework(),
                      link_size=get_link_size(),
                      show_single_page=show_single_page_or_not(),
                      **kwargs)

    
def get_outlet_name(outlet):
    g.db = connect_db()
    results = query_db('SELECT name FROM outlets where url = ?', (outlet,), one=True)
    name=int(next(iter(results.values())))
    return name


# -----------------------------------------------------------------------------
# URL GENERATORS
# -----------------------------------------------------------------------------
@freezer.register_generator
def index_pages():
    pages = get_total_anon_pages()
    for page in range (1, int(pages)):
        yield '/page/' + str(page) + '/'


@freezer.register_generator
def outlet_pages():
    outlets = get_outlet_urls()
    g.db = connect_db()
    for each outlet in outlets:
        results = query_db('SELECT count(*) FROM anon where source = ?', (outlet,), one=True)
        total=int(next(iter(results.values())))
        num_pages = total/PER_PAGE
        yield '/outlet/' + outlet_name + '/page/' + str(page)
    
    
# -----------------------------------------------------------------------------
# ROUTES
# -----------------------------------------------------------------------------
@app.route('/')
def index():
    total = query_db('select count(*) from anon', '', one=True)
#   TODO: Find more elegant way to deal with per_page, offset, etc.
    page, per_page, offset = get_page_items()
    results = query_db('SELECT anon.source, '
                       'outlets.name, '
                       'anon.phrase, '
                       'anon.title, '
                       'anon.link, '
                       'anon.content, '
                       'anon.date_entered '
                       'FROM '
                       'anon '
                       'LEFT OUTER JOIN '
                       'outlets '
                       'ON '
                       'anon.source = outlets.url '
                       'ORDER BY '
                       'date_entered DESC '
                       'LIMIT ?, ?', (offset, per_page))
    outlets = query_db("SELECT DISTINCT "
                       "outlets.name, "
                       "outlets.url "
                       "FROM outlets "
                       "JOIN anon "
                       "ON outlets.url = anon.source "
                       "ORDER BY outlets.name")
    pagination = get_pagination(page=page,
                                per_page=per_page,
                                total=next(iter(total.values())),
                                format_total=True,
                                format_number=True,
                                display_msg = '',
                                href='/page/{0}/'
                                )
    return render_template('index.html',
                           entries=results,
                           page=page,
                           per_page=per_page,
                           outlets=outlets,
                           pagination=pagination)


@app.route('/page/<int:page>/')
def index_pages(page):
    per_page = request.args.get('per_page')
    if not per_page:
        per_page = PER_PAGE
    else:
        per_page = int(per_page)
    offset = (page - 1) * per_page
    total = query_db('select count(*) from anon', '', one=True)
    results = query_db('SELECT anon.source, '
                       'outlets.name, '
                       'anon.phrase, '
                       'anon.title, '
                       'anon.link, '
                       'anon.content, '
                       'anon.date_entered '
                       'FROM '
                       'anon '
                       'LEFT OUTER JOIN '
                       'outlets '
                       'ON '
                       'anon.source = outlets.url '
                       'ORDER BY '
                       'date_entered DESC '
                       'LIMIT ?, ?', (offset, per_page))
    outlets = query_db("SELECT DISTINCT "
                       "outlets.name, "
                       "outlets.url "
                       "FROM outlets "
                       "JOIN anon "
                       "ON outlets.url = anon.source "
                       "ORDER BY outlets.name")
    pagination = get_pagination(page=page,
                                per_page=per_page,
                                total=next(iter(total.values())),
                                format_total=True,
                                format_number=True,
                                display_msg = '',
                                href='/page/{0}/'
                                )
    return render_template('index.html',
                           entries=results,
                           page=page,
                           per_page=per_page,
                           outlets=outlets,
                           pagination=pagination)


@app.route('/outlet/<outlet_name>/')
def outlet(outlet_name):
    masthead = parse.unquote_plus(outlet_name)
    outlet_name_dict = fetch_outlet_url(outlet_name)
    outlet_url = outlet_name_dict['url']
    total = query_db('select count(*) from anon LEFT OUTER JOIN outlets ON anon.source = outlets.url WHERE anon.source = ?', (outlet_url,), one=True)
    page, per_page, offset = get_page_items()
    results = query_db("SELECT "
                       "anon.link, "
                       "outlets.name, "
                       "anon.source, "
                       "anon.phrase, "
                       "anon.title, "
                       "anon.content, "
                       "anon.date_entered "
                       "FROM "
                       "anon "
                       "LEFT OUTER JOIN outlets "
                       "ON anon.source = outlets.url "
                       "WHERE anon.source = ? "
                       "ORDER BY anon.date_entered DESC "
                       "LIMIT ?, ?", (outlet_url, offset, per_page))
    outlets = query_db("SELECT DISTINCT "
                       "outlets.name, "
                       "outlets.url "
                       "FROM outlets "
                       "JOIN anon "
                       "ON outlets.url = anon.source "
                       "ORDER BY outlets.name")
    pagination = get_pagination(page=page,
                                per_page=per_page,
                                total=next(iter(total.values())),
                                format_total=True,
                                format_number=True,
                                display_msg='',
                                href="/outlet/" + outlet_name + "/page/{0}/"
                                )
    return render_template('outlet.html',
                           entries=results,
                           page=page,
                           per_page=per_page,
                           masthead=masthead,
                           outlets=outlets,
                           pagination=pagination)


@app.route('/outlet/<outlet_name>/page/<int:page>/')
def outlet_pages(outlet_name, page):
    masthead = parse.unquote_plus(outlet_name)
    outlet_name_dict = fetch_outlet_url(outlet_name)
    outlet_url = outlet_name_dict['url']
    total = query_db('select count(*) from anon LEFT OUTER JOIN outlets ON anon.source = outlets.url WHERE anon.source = ?', (outlet_url,), one=True)
    per_page = request.args.get('per_page')
    if not per_page:
        per_page = PER_PAGE = 50;
    else:
        per_page = int(per_page)
    offset = (page - 1) * per_page
    results = query_db("SELECT "
                       "anon.link, "
                       "outlets.name, "
                       "anon.source, "
                       "anon.phrase, "
                       "anon.title, "
                       "anon.content, "
                       "anon.date_entered "
                       "FROM "
                       "anon "
                       "LEFT OUTER JOIN outlets "
                       "ON anon.source = outlets.url "
                       "WHERE anon.source = ? "
                       "ORDER BY anon.date_entered DESC "
                       "LIMIT ?, ?", (outlet_url, offset, per_page))
    outlets = query_db("SELECT DISTINCT "
                       "outlets.name, "
                       "outlets.url "
                       "FROM outlets "
                       "JOIN anon "
                       "ON outlets.url = anon.source "
                       "ORDER BY outlets.name")
    pagination = get_pagination(page=page,
                                per_page=per_page,
                                total=next(iter(total.values())),
                                format_total=True,
                                format_number=True,
                                display_msg='',
                                href="/outlet/" + outlet_name + "/page/{0}/"
                                )
    return render_template('outlet.html',
                           entries=results,
                           page=page,
                           per_page=per_page,
                           masthead=masthead,
                           outlets=outlets,
                           pagination=pagination)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        freezer.freeze()
    else:
#        app.run(debug=True)
        freezer.run(debug=True)
        

