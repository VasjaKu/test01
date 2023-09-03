import os
import psycopg2
import math
import random
import hashlib
from flask import session
from flask_session import Session
from flask import Flask
from flask import render_template
from flask import request
from flask import redirect, url_for, make_response
app = Flask(__name__)
app.secret_key = 'zzzzzzzdqfwefegergnergwjnbrbjnrekbnwelrkbne'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def create_cookie():
   rand = random.randrange(1, 1000000000)
   ha = hashlib.md5(str(rand).encode()).hexdigest()
   return ha

def is_authorized(session):
    if session.get('username') != None:
        return True
    else:
        return False

@app.route('/logout')
def logout():
    if is_authorized(session):
        session.clear()
    return redirect(url_for('authorisation'), code=302)

def get_param(param_name):
    if request.method == 'POST':
        query = request.form.get(param_name)
    else:
        query = request.args.get(param_name)
    return query

def get_db_connection():
    try:
        conn = psycopg2.connect(host='192.168.56.1', port=5432, dbname= 'postgres', user='postgres', password='Cr0ssout')
    except psycopg2.OperationalError as e:
        print(e)
    else:
        print('Connected!')
    return conn

@app.route('/')
@app.route('/index')
def index():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    conn = get_db_connection()
    cur = conn.cursor()
    #return str(type(cur))+'ZZZ'
    cur.execute("""
        select id_w, place, path
        from warehouse_view
        order by path
    """)
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', data=data)

@app.route('/place', methods=['GET', 'POST'])
def place():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    warehouse_id = request.args.get('warehouse_id')
    title = request.args.get('title');
    sql = "select id_i, item, serial_number, id_w,path, place, recordings_id, quantity,available ,f_date, l_date from recordings_view where id_w = %s"
    conn = get_db_connection()
    #cur = conn.cursor()
    cur.execute(sql, (warehouse_id))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('place.html', data=data, title=title)

@app.route('/items', methods=['GET', 'POST'])
def items():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    conn = get_db_connection()
    cur = conn.cursor()
    limit = get_param('limit')
    if limit is None or limit == '':
        limit = 10
    else:
        limit = int(limit)
    if get_param('offset') is None or get_param('offset') == '':
        offset = 0
    else:
        offset = int(get_param('offset'))
    #return str(type(cur))+'ZZZ'
    cur.execute("""
        select count(*) as cnt
        from items""");
    data = cur.fetchall()
    total = float(data[0][0]);
    pages = math.ceil(total / limit)
    page = math.floor(offset / limit)
    if (page <= 0):
        previous_page = 0
    else:
        previous_page = (page - 1)*limit
    if (page >= pages):
       next_page = pages*limit
    else:
       next_page = (page + 1)*limit
    if next_page >= total:
       next_page = next_page - limit
    last_page = int(total // limit)*limit

    cur.execute("""
        select id_i, item, serial_number
        from items
        order by lower(item), id_i
        limit """+str(limit)+' offset '+str(offset))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('items.html', data=data, next=next_page, prev=previous_page, first=0, last=last_page, limit=limit)

@app.route('/item', methods=['GET', 'POST'])
def item():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    item_id = request.args.get('item_id')
    title = request.args.get('item_name')
    sql = "select id_i, item, serial_number, id_w,path, place, recordings_id, quantity,available ,f_date, l_date from recordings_view where id_i = %s"
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(sql, (item_id))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('item.html', data=data, title=title)

@app.route('/search', methods=['GET', 'POST'])
def do_search():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    #if request.method == 'POST':
    #    query = request.form['q']
    #else:
    #    query = request.args.get('q');
    #return query;
    query = get_param('q')
    #return query
    #return sql
    conn = get_db_connection()
    cur = conn.cursor()
    #return 'aaa'
    limit = get_param('limit')
    if limit is None:
        limit = 10
    else:
        limit = int(limit)
    if get_param('offset') is None:
        offset = 0
    else:
        offset = int(get_param('offset'))
    #return '['+str(limit)+']'
    #sql = "select count(*) from (select 1 as a from items where lower(items.item) like '%"+query.lower()+"%' union all select 1 as a from warehouse where lower(warehouse.place) like '%"+query.lower()+"%') b"
    sql = "select count(*) from (select 1 as a from items where lower(items.item) like %s union all select 1 as a from warehouse where lower(warehouse.place) like %s) b"
    #print(sql, ( '%'+query.lower()+'%', '%'+query.lower()+'%' ))
    cur.execute(sql, ( '%'+query.lower()+'%', '%'+query.lower()+'%' ));
    data = cur.fetchall()
    total = float(data[0][0]);
    pages = math.ceil(total / limit)
    page = math.floor(offset / limit)
    if (page <= 0):
        previous_page = 0
    else:
        previous_page = (page - 1)*limit
    if (page >= pages):
       next_page = pages*limit
    else:
       next_page = (page + 1)*limit
    if next_page >= total:
       next_page = next_page - limit
    last_page = int(total // limit)*limit
    #sql = "select id_i as id, item, '/item?item_id='||id_i::varchar(10)||'&item_name='||item as type from items where lower(items.item) like '%"+query.lower()+"%' union all select id_w, place, '/place?warehouse_id='||id_w::varchar(10)||'&title='||place from warehouse where lower(warehouse.place) like '%"+query.lower()+"%'"
    sql = "select id_i as id, item, '/item?item_id='||id_i::varchar(10)||'&item_name='||item as type from items where lower(items.item) like %s union all select id_w, place, '/place?warehouse_id='||id_w::varchar(10)||'&title='||place from warehouse where lower(warehouse.place) like %s"
    sql = sql + " limit %s offset %s"
    #return sql
    cur.execute(sql, ('%'+query.lower()+'%', '%'+query.lower()+'%', limit, offset))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('search_results.html', data=data, next=next_page, prev=previous_page, first=0, last=last_page, limit=limit, q=query)

@app.route('/reg', methods=['GET', 'POST'])
def registration():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    if session['user_role'] != 2:
        return 'Твоя здесь низя!<br>'
    query1 = get_param('q1')
    query2 = get_param('q2')
    query3 = get_param('q3')
    data = [query1, query2, query3]
    conn = get_db_connection()
    cur = conn.cursor()
    sql = "select id_r, role from roles order by role"
    cur.execute(sql)
    data = cur.fetchall() 
    cur.close()
    conn.close()
    return render_template('reg.html', q1=query1, q2=query2, q3=query3, data = data)

@app.route('/reg_res', methods=['GET', 'POST'])
def registration_result():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    if session['user_role'] != 2:
        return 'Твоя здесь низя!<br>'
    query1 = get_param('q1')
    query2 = get_param('q2')
    query3 = get_param('q3')
    conn = get_db_connection()
    cur = conn.cursor()
    sql = "select count(*) from (select 1 as a from users where users.username = %s) b"
    cur.execute(sql, (query1, ))
    data = cur.fetchall()
    if data[0][0] == 0:
        if query2 == query3:
            rand = random.randrange(1, 1000000000)
            salt = hashlib.md5(str(rand).encode()).hexdigest()
            string = query2 + salt
            ha = hashlib.md5(string.encode())
            #sql = "insert into users(username, salt, pass, ban, user_role) values ('"+query1+"', '"+salt+"', '"+ha.hexdigest()+"', 'Yes', '"+get_param('role')+"')"
            sql = "insert into users(username, salt, pass, ban, user_role) values (%s, %s, %s, %s, %s)"
            #print(sql)
            #cur.execute(sql)
            cur.execute(sql, (query1, salt, ha.hexdigest(), 'Yes', get_param('role')))
            conn.commit()
            string1 = "Регистрация успешно завершена!"
            string2 = "Теперь вам доступно ровно 0 новых фишек!"
            session['username'] = query1
        else:
            string1 = "Регистрация успешно провалена!"
            string2 = "Видимо, Ваши пароли не совпадают. Вернитесь на окно регистрации и введите 2 одинаковых пароля."
    else:
        string1 = "Регистрация успешно провалена!"
        string2 = "Видимо, пользователь с таким никнеймом уже есть. Пожалуйста, введите другое имя."
    data = [string1, string2]
    cur.close()
    conn.close()
    return render_template('reg_res.html', data = data)

@app.route('/login', methods=['GET', 'POST'])
def authorisation():
    query1 = get_param('q1')
    query2 = get_param('q2')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.close()
    conn.close()
    return render_template('login.html', q1=query1, q2=query2)

@app.route('/login_res', methods=['GET', 'POST'])
def authorisation_result():
    query1 = get_param('q1')
    query2 = get_param('q2')
    conn = get_db_connection()
    cur = conn.cursor()
    #sql = "select count(*) from (select 1 as a from users where users.username = '"+query1+"') b"
    sql = "select count(*) from (select 1 as a from users where users.username = %s) b"
    #cur.execute(sql)
    cur.execute(sql, (query1, ))
    data = cur.fetchall();
    is_authorized = False
    if data[0][0] == 0:
        string1 = "Авторизация успешно провалена!"
        string2 = "Такого никнейма нет в базе дынных. Введите другое имя или зарегистрируйтесь!"
    else:
        #sql = "select salt, pass, ban, user_role from users where users.username = '"+query1+"'"
        sql = "select salt, pass, ban, user_role from users where users.username = %s"
        #cur.execute(sql)
        cur.execute(sql, (query1, ))
        data = cur.fetchall();
        string = query2 + data[0][0]
        ha = hashlib.md5(string.encode())
        if data[0][2] == "Yes" and data[0][1] == ha.hexdigest():
            string1 = "Авторизация успешно завершена!"
            string2 = "Это не изменило ровным счётом ничего!"
            session['username'] = query1
            session['user_role'] = data[0][3]
            is_authorized = True
        elif data[0][2] == "No":
            string1 = "Авторизация успешно завершена!"
            string2 = "Но вы забанены."
        else:
            string1 = "Регистрация успешно провалена!"
            string2 = "Видимо, Вы указали неверный пароль."
    data = [string1, string2]
    cur.close()
    conn.close()
    resp = make_response(render_template('login_res.html', data = data))
    #if is_authorized == True:
    #    resp.set_cookie('session_id', create_cookie())
    return resp
