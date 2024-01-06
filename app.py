import os
import psycopg2
import math
import random
import hashlib
from time import time
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
    sql = "select item_id, item, warehouse_id, place, total_q, total_amount from recordings where warehouse_id = %s"
    conn = get_db_connection()
    cur = conn.cursor()
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
        from total_count""");
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
    if (int(total // limit)*limit == (int(total // limit)*limit)):
        last_page = int(total // limit)*limit - limit
    else:
        last_page = int(total // limit)*limit
    cur.execute("""
        select item_id, item, total_q, total_amount
        from total_count
        order by lower(item), item_id
        limit """+str(limit)+' offset '+str(offset))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('items.html', data=data, next=next_page, prev=previous_page, first=0, last=last_page, limit=limit)

@app.route('/item', methods=['GET', 'POST'])
def item():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    sql = "select is_serial_number from items where id_i = %s"
    conn = get_db_connection()
    cur2 = conn.cursor()
    cur2.execute(sql, (request.args.get('item_id')))
    is_serial_number = cur2.fetchall()
    cur2.close()
    conn.close()
    if is_serial_number[0][0] == False:    
        item_id = request.args.get('item_id')
        title = request.args.get('item_name')
        sql = "select warehouse_id, place, total_q, total_amount, i_s_n from recordings where item_id = %s"
    else:
        item_id = request.args.get('item_id')
        title = request.args.get('item_name')
        sql = """
            SELECT warehouse.place,
                aaa.item_id,
                aaa.warehouse_id,
                aaa.item,
                aaa.lot_id,
                sum(aaa.total_q) AS total_q,
                sum(aaa.total_amount) AS total_amount,
                aaa.s_n
               FROM ( SELECT i.item,
                        i.id_i AS item_id,
                        l.id_l AS lot_id,
                        l.item_id AS item_id_from_lot,
                        l.price AS lot_price,
                        d.warehouse_id,
                        w.id_w,
                        sum(d.quantity_change) AS total_q,
                        sum(d.quantity_change)::double precision * l.price AS total_amount,
                        l.serial_number AS s_n
                       FROM items i,
                        lots l,
                        debit_credit d,
                        warehouse w
                      WHERE d.lot_id = l.id_l AND d.warehouse_id = w.id_w
                      GROUP BY i.item, d.warehouse_id, i.id_i, l.id_l, l.price, l.quantity, w.id_w) aaa, warehouse
              WHERE aaa.id_w = warehouse.id_w AND aaa.item_id = %s
              GROUP BY aaa.lot_id, warehouse.place, aaa.item_id, aaa.item, aaa.warehouse_id, aaa.s_n;
        """
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
    #if not is_authorized(session):
    #    return redirect(url_for('authorisation'), code=302)
    #if session['user_role'] != 2:
    #    return 'Твоя здесь низя!<br>'
    query1 = get_param('q1')
    query2 = get_param('q2')
    query3 = get_param('q3')
    data = [query1, query2, query3]
    conn = get_db_connection()
    cur = conn.cursor()
    sql = "select id_ro, role from roles order by role"
    cur.execute(sql)
    data = cur.fetchall() 
    cur.close()
    conn.close()
    return render_template('reg.html', q1=query1, q2=query2, q3=query3, data = data)

@app.route('/reg_res', methods=['GET', 'POST'])
def registration_result():
    #if not is_authorized(session):
    #    return redirect(url_for('authorisation'), code=302)
    #if session['user_role'] != 2:
    #    return 'Твоя здесь низя!<br>'
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
            sql = "insert into users(username, salt, password, ban, role_id) values (%s, %s, %s, %s, %s)"
            #print(sql)
            #cur.execute(sql)
            cur.execute(sql, (query1, salt, ha.hexdigest(), 'false', get_param('role')))
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
        sql = "select salt, password, ban, role_id from users where users.username = %s"
        #cur.execute(sql)
        cur.execute(sql, (query1, ))
        data = cur.fetchall();
        string = query2 + data[0][0]
        ha = hashlib.md5(string.encode())
        if data[0][2] == False and data[0][1] == ha.hexdigest():
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

@app.route('/ban', methods=['GET', 'POST'])
def ban():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    if session['user_role'] != 1:
        return 'Твоя здесь низя!<br>'
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
    sql = "select count(*) from users"
    cur.execute(sql)
    data = cur.fetchall()
    total = float(data[0][0]);
    number = data[0][0]
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
    sql = "select id_u, role_id, username, ban from users order by id_u"
    user = session["username"]
    cur.execute(sql)
    data = cur.fetchall()
    strings = [[0] * 2 for i in range(number)]
    for i in range(number):
        if data[i][2] == "Yes" and session["username"] == data[i][1]:
            string_a = "Yes"
            string_b = "Вы не можете расстрелять сами себя!"
        elif data[i][2] == "Yes":
            string_a = "No"
            string_b = "Расстрелять!"
        else:
            string_a = "Yes"
            string_b = "Амнистировать!"
        strings[i][0] = string_a
        strings[i][1] = string_b
    return render_template('ban.html', data=data, next=next_page, prev=previous_page, first=0, last=last_page, limit=limit, user = user, strings = strings, number = number)

@app.route('/ban_result', methods = ['GET', 'POST'])
def ban_result():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    if session['user_role'] != 1:
        return 'Твоя здесь низя!<br>'
    id_u = request.args.get('id_u')
    ban = request.args.get('ban')
    conn = get_db_connection()
    cur = conn.cursor()
    sql = "select username from users where id_u = %s"
    cur.execute(sql, (id_u, ))
    name = cur.fetchall()
    sql = "update users set ban = %s where id_u = %s"
    cur.execute(sql, (ban, id_u))
    conn.commit()
    if session["username"] == name[0][0]:
        words = "Нельзя расстрелять самого себя!"
    elif ban == True:
        words = "Пользователь был амнистирован!"
    else:
        words = "Именем админа Вы приговариваетесь к расстрелу! *Пыщ!*"
    #data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('ban_result.html', time = time(), words = words)

@app.route('/add_tmc', methods = ['GET', 'POST'])
def add_tmc():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    if session['user_role'] != 1:
        return 'Твоя здесь низя!<br>'
    query1 = get_param('q1')
    query2 = get_param('q2')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.close()
    conn.close()
    return render_template('add_tmc.html', q1=query1, q2=query2)

@app.route('/add_tmc_result', methods=['GET', 'POST'])
def tmc_result():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    if session['user_role'] != 1:
        return 'Твоя здесь низя!<br>'
    query1 = get_param('q1')
    query2 = get_param('q2')
    conn = get_db_connection()
    cur = conn.cursor()
    sql = "select count(*) from (select 1 as a from items where items.item = %s) b"
    cur.execute(sql, (query1, ))
    data = cur.fetchall()
    if data[0][0] == 0:
        if str(query2) == "0":
            sql = "insert into items (item) values (%s)"
            cur.execute(sql, (query1, ))
            conn.commit()
            string1 = "Добавлен ТМЦ"
            string2 = "Товар успешно внесён в список!"
        else:
            sql = "insert into items (item, serial_number) values (%s, %s)"
            cur.execute(sql, (query1, query2, ))
            conn.commit()
            string1 = "Добавлен ТМЦ"
            string2 = "Товар успешно внесён в список!"
    else:
        string1 = "Ошибка!"
        string2 = "Видимо, такой товар уже существует"
    data = [string1, string2]
    cur.close()
    conn.close()
    return render_template('add_tmc_result.html', data = data)

@app.route('/change_tmc', methods = ['GET', 'POST'])
def change_tmc():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    if session['user_role'] != 1:
        return 'Твоя здесь низя!<br>'
    query1 = get_param('item_name')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.close()
    conn.close()
    return render_template('change_tmc.html', q1=query1)

@app.route('/change_tmc_result', methods=['GET', 'POST'])
def change_tmc_result():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    if session['user_role'] != 2:
        return 'Твоя здесь низя!<br>'
    id_i = get_param("old_name")
    print(id_i)
    query1 = get_param('q1')
    query2 = get_param('q2')
    conn = get_db_connection()
    cur = conn.cursor()
    sql = "select count(*) from (select 1 as a from items where items.item = %s) b"
    cur.execute(sql, (id_i, ))
    data = cur.fetchall()
    if data[0][0] != 0:
        if str(query2) == "0":
            sql = "update items set item = %s where items.item = %s"
            cur.execute(sql, (query1, id_i, ))
            conn.commit()
            string1 = "Добавлен ТМЦ"
            string2 = "Товар успешно внесён в список!"
        else:
            sql = "update items set item = %s , serial_number = %s where items.item = %s"
            cur.execute(sql, (query1, query2, id_i, ))
            conn.commit()
            string1 = "Добавлен ТМЦ"
            string2 = "Товар успешно внесён в список!"
    else:
        string1 = "Ошибка!"
        string2 = "Видимо, такой товар ещё не существует!"
    data = [string1, string2]
    cur.close()
    conn.close()
    return render_template('change_tmc_result.html', data = data)

@app.route('/put_tmc', methods = ['GET', 'POST'])
def put_tmc():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    if session['user_role'] != 1:
        return 'Твоя здесь низя!<br>'
    sql = "select id_w, id_u, f_date from"
    query1 = get_param('q1')
    query2 = get_param('q2')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.close()
    conn.close()
    return render_template('put_tmc.html', q1=query1, q2 = query2)

@app.route('/put_tmc_result', methods=['GET', 'POST'])
def put_tmc_result():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    if session['user_role'] != 1:
        return 'Твоя здесь низя!<br>'
    query1 = get_param('q1')
    query2 = get_param('q2')
    conn = get_db_connection()
    cur = conn.cursor()
    sql = "select count(*) from (select 1 as a from items where items.item = %s) b"
    cur.execute(sql, (query1, ))
    data = cur.fetchall()
    if data[0][0] == 0:
        if str(query2) == "0":
            sql = "insert into items (item) values (%s)"
            cur.execute(sql, (query1, ))
            conn.commit()
            string1 = "Добавлен ТМЦ"
            string2 = "Товар успешно внесён в список!"
        else:
            sql = "insert into items (item, serial_number) values (%s, %s)"
            cur.execute(sql, (query1, query2, ))
            conn.commit()
            string1 = "Добавлен ТМЦ"
            string2 = "Товар успешно внесён в список!"
    else:
        string1 = "Ошибка!"
        string2 = "Видимо, такой товар уже существует"
    data = [string1, string2]
    cur.close()
    conn.close()
    return render_template('put_tmc_result.html', data = data)

@app.route('/debit-credit', methods = ['GET', 'POST'])
def debit_credit():
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
    if offset < 0:
        offset = 0
    #return str(type(cur))+'ZZZ'
    cur.execute("""
        select count(*) as cnt
        from debit_credit""");
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
    if (int(total // limit)*limit == (int(total // limit)*limit)):
        last_page = int(total // limit)*limit - limit
    else:
        last_page = int(total // limit)*limit
    cur.execute("""
        select id_dc, lot_id, place, username, date, quantity_change
        from debit_credit, warehouse, users
        where warehouse.id_w = debit_credit.warehouse_id and users.id_u = debit_credit.user_id
        order by id_dc, date, user_id, quantity_change
        limit """+str(limit)+' offset '+str(offset))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('debit_credit.html', data=data, next=next_page, prev=previous_page, first=0, last=last_page, limit=limit)
