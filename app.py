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
    if offset < 0:
        offset = 0
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
            sql = "insert into items (item, is_serial_number) values (%s, false)"
            cur.execute(sql, (query1, ))
            conn.commit()
            string1 = "Добавлен ТМЦ"
            string2 = "Товар успешно внесён в список!"
        else:
            sql = "insert into items (item, is_serial_number) values (%s, true)"
            cur.execute(sql, (query1, ))
            conn.commit()
            string1 = "Добавлен ТМЦ."
            string2 = "Товар успешно внесён в список!"
    else:
        string1 = "Ошибка!"
        string2 = "Видимо, такой товар уже существует."
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
    return render_template('change_tmc.html', q1=query1)

@app.route('/change_tmc_result', methods=['GET', 'POST'])
def change_tmc_result():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    if session['user_role'] != 1:
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
        select 
          id_dc, 
          lot_id, 
          place, 
          username, 
          date, 
          quantity_change,
          u.role_id,
          r.role
         from debit_credit dc, 
              warehouse w, 
              users u,
              roles r
         where w.id_w = dc.warehouse_id 
           and u.id_u = dc.user_id
           and u.role_id = r.id_ro
        order by id_dc,
           date,
           user_id,
           quantity_change
        limit """+str(limit)+' offset '+str(offset))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('debit_credit.html', data=data, next=next_page, prev=previous_page, first=0, last=last_page, limit=limit)

@app.route('/sorted-debit-credit', methods = ['GET', 'POST'])
def sorted_debit_credit():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    query1 = get_param('q1')# роль
    query2 = get_param('q2')# юзер
    query3 = get_param('q3')# товар
    query4 = get_param('q4')# партия
    query5 = get_param('q5')# место хранения
    query6 = get_param('q6')# дата начала
    query7 = get_param('q7')# дата конца
    data = [query1, query2, query3, query4, query5, query6, query7]
    return render_template('sorted-debit-credit.html', q1=query1, q2=query2, q3=query3, q4=query4, q5=query5, q6=query6, q7=query7)

@app.route('/sorted-debit-credit-result', methods = ['GET', 'POST'])
def sorted_debit_credit_result():
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
# не забудь пагинацию ДОДЕЛАТЬ!
    query1 = get_param('q1')# роль
    query2 = get_param('q2')# юзер
    query3 = get_param('q3')# место хранения
    query4 = get_param('q4')# товар
    query5 = get_param('q5')# партия
    query6 = get_param('q6')# дата начала
    query7 = get_param('q7')# дата конца
    sql1, sql2, sql3, sql4, sql5, sql6, sql7 = '', '', '', '', '', '', ''
    if query1 != '':
        sql1 = ' and u.role_id = %s'
    sql = """
        select 
          id_dc, 
          lot_id, 
          place, 
          username, 
          date, 
          quantity_change,
          u.role_id,
          r.role
         from debit_credit dc, 
              warehouse w, 
              users u,
              roles r
         where w.id_w = dc.warehouse_id 
           and u.id_u = dc.user_id
           and u.role_id = r.id_ro"""

    sql_end = "order by id_dc, date, user_id, quantity_change)"
    cur.execute(sql, ())
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
    sql = """
            select
                id_dc,
                case when %s = null then (select role from roles)
                else (select role from roles where roles.id_ro = %s)
                end as role,
                case when %s = null then (select username from users)
                else (select username from users where users.id_u in %s)
                end as username,
                case when %s = null then (select place from warehouse)
                else (select place from warehouse where warehouse.id_w in %s)
                end as place,
                case when %s = null then (select item from items)
                else (select item from items where items.id_i in %s)
                end as goods,
                case when %s = null then (select id_l from lots)
                else (select id_l from lots where lots.id_l in %s)
                end as id_l,
                case when %s = null and %s = null then (select date from debit_credit)
                case when %s = null then (select date from debit_credit where debit_credit.date < %s)
                case when %s = null then (select date from debit_credit where debit_credit.date > %s)
                else (select date from debit_credit where debit_credit.date > %s and debit_credit.date < %s)
                end as date,
                quantity_change
              from debit_credit, warehouse, users
              where roles.id_ro = users.role_id and users.id_u = debit_credit.user_id and warehouse.id_w = debit_credit.warehouse_id and users.id_u = debit_credit.user_id and debit_credit.lot_id = lots.id_l
              order by id_dc, date, user_id, quantity_change
    """
    cur.execute(sql, (query1, query1, query2, query2, query3, query3, query4, query4, query5, query5, query6, query7, query6, query7, query7, query6, query6, query7))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('sorted-debit-credit-result.html', data = data, next=next_page, prev=previous_page, first=0, last=last_page, limit=limit)
#-------------------------------------------------------- Временно неиспользуемый кусок кода. Потом переделаю для добавления ТМЦ в места хранения. ------------
@app.route('/add-debit-credit-1', methods = ['GET', 'POST'])
def add_debit_credit_1():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    conn = get_db_connection()
    cur = conn.cursor()
    sql = "select item, id_i from items order by item"
    cur.execute(sql)
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('add_debit_credit_1.html', data = data)

@app.route('/add-debit-credit-2', methods = ['GET', 'POST'])
def add_debit_credit_2():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    conn = get_db_connection()
    cur = conn.cursor()
    sql = "select id_l, price, created_at, serial_number, quantity from lots where item_id = %s"
    cur.execute(sql, (get_param('item'), ))
    data = cur.fetchall() 
    query2 = data[0][0]
    cur.close()
    conn.close()
    return render_template('add_debit_credit_2.html', q2 = query2, data = data)

@app.route('/add-debit-credit-3', methods = ['GET', 'POST'])
def add_debit_credit_3():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    conn = get_db_connection()
    cur = conn.cursor()
    query2 = get_param('lot')
    sql = "select place, id_w from warehouse order by id_w"
    cur.execute(sql)
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('add_debit_credit_3.html', q2 = query2, data = data)

@app.route('/add-debit-credit-4', methods = ['GET', 'POST'])
def add_debit_credit_4():
# тут у нас квантити чэйндж, так что, опять же, нужно прописать, что берём количество из лота, либо из дебит-кредит (короче тоже надо продумать)
# так как в дебит-кредит можно положить не весь лот сразу, а также возвращать то, что забрали, алгоритм слудующий:
# сначала смотрим, есть ли запись лота в дебит-кредите
# если есть, то ограничение - кол-во внутри самого лота
# иначе - смотрим на то, больше нуля или меньше заданное число
# если число больше 0, то мы кладём вещь, т.е. ограничение - кол-во лота - кол-во того, что уже положили в места хранения вообще.
# если число меньше 0, то мы берём вещь из места хранения, т.е. ограничение - кол-во того, что лежит в конкретно заданном месте хранения.
# Отдельный эррор будет на 0, ибо какого фига вы решили заспамить память бессполезной информацией?
# Итого, нужно вывести, сколько свободно в лоте вещей, сколько лежит в этом месте.
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    conn = get_db_connection()
    cur = conn.cursor()
    query1 = get_param('place')
    query2 = get_param('q2')
    sql1 = "select quantity, id_l from lots where id_l = %s"
    sql2 = "select sum(quantity_change), lot_id from debit_credit where lot_id = %s group by lot_id"
    sql3 = "select sum(quantity_change), lot_id from debit_credit where lot_id = %s and warehouse_id = %s group by lot_id"
    cur.execute(sql1, (query2, ))
    data1 = cur.fetchall() 
    cur.execute(sql2, (query2, ))
    data2 = cur.fetchall()
    if data2 == []:
        data2 = [[0]]
    dop = data1[0][0] - data2[0][0]
    cur.execute(sql3, (query2, query1))
    data3 = cur.fetchall()
    if data3 == []:
        data3 = [[0]]
    query3 = get_param('q3')
    print(query1)
    print(query2)
    print(data1)
    print(data2)
    print(data3)
    cur.close()
    conn.close()
    return render_template('add_debit_credit_4.html', q1 = query1, q2 = query2, q3 = query3, data1 = data1, data2 = data2, data3 = data3, dop = dop)

#@app.route('/add-debit-credit-5', methods = ['GET', 'POST'])
#def add_debit_credit_5():
# тут будет дата, так что нужно продумать, какие именно даты можно прописывать, и как определить ошибку.
# у нас есть пока ровно одна адекватная дата - дата создания лота, так что ограничение снизу есть. Но, раз мы мы туда-сюда двигаем части лота, то этого мало.
# Во-первых, желательно как-то не вылезти за рамки текущей даты, а, во-вторых, нужно как-то позволить задавать дату, причём не противоречащую другим записям.
#    if not is_authorized(session):
#        return redirect(url_for('authorisation'), code=302)
#    conn = get_db_connection()
#    cur = conn.cursor()
#    query2 = get_param('q2')
#    query3 = get_param('q3')
#    query4 = get_param('q4')
#    sql = "select item, id_i from items order by items.id_i"
#    cur.execute(sql)
#    data = cur.fetchall() 
#    cur.close()
#    conn.close()
#    return render_template('add_debit_credit_5.html', q2 = query2, q3 = query3, q4 = query4, data = data)

@app.route('/add-debit-credit-result', methods=['GET', 'POST'])
def add_debit_credit_result():
# query1 = place, query2 = lot, query3 = quantity
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    conn = get_db_connection()
    cur = conn.cursor()
    query1 = get_param('q1')
    query2 = get_param('q2')
    query3 = get_param('q3')
    sql1 = "select quantity, id_l from lots order by lots.id_l"
    sql2 = "select sum(quantity_change), lot_id from debit_credit where lot_id = %s group by lot_id"
    sql3 = "select sum(quantity_change), lot_id from debit_credit where lot_id = %s and warehouse_id = %s group by lot_id"
    cur.execute(sql1)
    data1 = cur.fetchall() 
    cur.execute(sql2, (query2, ))
    data2 = cur.fetchall()
    if data2 == []:
        data2 = [[0]]
    cur.execute(sql3, (query2, query1))
    data3 = cur.fetchall()
    if data3 == []:
        data3 = [[0]]
    try:
        query3 = int(query3)
    except ValueError:
        query3 = query3
    if type(query3) == int:
        query3 = int(query3)
        sql = "select id_u from users where users.username = %s"
        cur.execute(sql, (session['username'], ))
        data = cur.fetchall()
        if query3 > 0:
            if query3 > data1[0][0] - data2[0][0]:
                string1 = "Слишком много!"
                string2 = "Вы хотите положить предметов больше, чем у Вас есть в данный момент. Ну-ну. Губа не дура."
            else:
                sql = "insert into debit_credit (lot_id, warehouse_id, user_id, date, quantity_change) values (%s, %s, %s, current_timestamp, %s)"
                cur.execute(sql, (query2, query1, data[0][0], query3, ))
                conn.commit()
                string1 = "Операция прошла успешно!"
                string2 = "Спасибо, что доверили нам Ваши вещи!"
        elif query3 < 0:
            if -1 * query3 > data3[0][0]:
                string1 = "Слишком много!"
                string2 = "Вы хотите забрать предметов больше, чем их тут лежит. Не дам!"
            else:
                sql = "insert into debit_credit (lot_id, warehouse_id, user_id, date, quantity_change) values (%s, %s, %s, current_timestamp, %s)"
                cur.execute(sql, (query2, query1, data[0][0], query3, ))
                conn.commit()
                string1 = "Операция прошла успешно!"
                string2 = "Возвращаем Вам вверенные нам вещи!"
        else:
            string1 = "Каков наглец!"
            string2 = "Не дам я тебе 0-е значение записать. У меня память не бесконечная!"
        cur.close()
        conn.close()
    else:
            string1 = "Вы ввели дребедень вместо количества товаров!"
            string2 = "А я покажу экран ошибки вместо добавления новой записи! Бе!"
    data = [string1, string2]
    cur.close()
    conn.close()
    return render_template('add_debit_credit_result.html', data = data)
#-------------------------------------------------------- Временно неиспользуемый кусок кода. Потом переделаю для добавления ТМЦ в места хранения. ------------

@app.route('/lots', methods = ['GET', 'POST'])
def lots():
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
        from lots""");
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
        select id_l, item, price, quantity, serial_number, created_at
        from lots, items
        where lots.item_id = items.id_i
        order by item, created_at, price, quantity, serial_number
        limit """+str(limit)+' offset '+str(offset))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('lots.html', data=data, next=next_page, prev=previous_page, first=0, last=last_page, limit=limit)

@app.route('/add-lot', methods=['GET', 'POST'])
def add_lot():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    if session['user_role'] != 1:
        return 'Твоя здесь низя!<br>'
    conn = get_db_connection()
    cur = conn.cursor()
    query2 = get_param('q2')
    query3 = get_param('q3')
    query4 = get_param('q4')
    sql = "select item, id_i from items order by items.id_i"
    cur.execute(sql)
    data = cur.fetchall() 
    cur.close()
    conn.close()
    return render_template('add_lot.html', q2 = query2, q3 = query3, q4 = query4, data = data)

@app.route('/add-lot-result', methods=['GET', 'POST'])
def add_lot_result():
    if not is_authorized(session):
        return redirect(url_for('authorisation'), code=302)
    if session['user_role'] != 1:
        return 'Твоя здесь низя!<br>'
    query2 = (get_param('q2'))
    query3 = (get_param('q3'))
    query4 = get_param('q4')
    conn = get_db_connection()
    cur = conn.cursor()
    if query2.isdigit() and query3.isdigit():
        query2 = int(query2)
        query3 = int(query3)
        if (query4 != "0") and (query3 != 1):
            string1 = "Ошибка!"
            string2 = "В партии товара с серийным номером может быть только 1 предмет."
        elif query2 <= 0:
            string1 = "Ошибка!"
            string2 = "Не шути. Просто поставь цену."
        elif query3 <= 0:
            string1 = "Ошибка!"
            string2 = "Нельзя положить ничто, или отрицательно существующий объект. Как только это будет возможно - мы Вас уведомим."
        elif str(query2) == "0":
            sql = "insert into lots (item_id, price, created_at, quantity) values (%s, %s, current_timestamp, %s)"
            cur.execute(sql, (get_param('tmc'), query2, query3))
            conn.commit()
            string1 = "Добавлена новая партия."
            string2 = "Партия успешно добавлена!"
        else:
            sql = "insert into lots (item_id, price, created_at, serial_number, quantity) values (%s, %s, current_timestamp, %s, %s)"
            cur.execute(sql, (get_param('tmc'), query2, query4, query3))
            conn.commit()
            string1 = "Добавлена новая партия."
            string2 = "Партия успешно добавлена!"
    else:
        string1 = "Поздравляю! Вы ввели всякую дребедень вместо обычных цифр!"
        string2 = "В качестве награды можете полюбоваться этим экраном ошибки!"
    data = [string1, string2]
    cur.close()
    conn.close()
    return render_template('add_lot_result.html', data = data)

