from flask import Flask, redirect, request, render_template, session, url_for, flash, send_from_directory
import pymysql
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

db_config = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': os.getenv('DB_PASSWORD'),
    'db': 'board',
    'charset': 'utf8mb4'
}

def init_db():

    config = db_config
    conn = None
    try:
        server_conn_info = config.copy()
        db_name = server_conn_info.pop('db')
        conn = pymysql.connect(**server_conn_info)
    
        with conn.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
                    conn.select_db(db_name)

        with conn.cursor() as cursor:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS topic (
            id INT PRIMARY KEY AUTO_INCREMENT,
            title VARCHAR(255) NOT NULL,
            body TEXT NOT NULL
            )
            """
            cursor.execute(create_table_sql)

        with conn.cursor() as cursor:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS users (
            id INT PRIMARY KEY AUTO_INCREMENT,
            user_id VARCHAR(100) NOT NULL,
            user_ps VARCHAR(255) NOT NULL,
            user_name VARCHAR(100) NOT NULL,
            user_school VARCHAR(100) NOT NULL
            )
            """
            cursor.execute(create_table_sql)
            
        conn.commit()    
        print("데이터베이스 연결 완료.")

    except Exception as e:
        print(f"오류 발생: {e}")
            
    finally:
            if conn:
                conn.close()

def get_db_connection():
    conn = pymysql.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        db=db_config['db'],
        charset=db_config['charset'],
        cursorclass=pymysql.cursors.DictCursor 
    )
    return conn

def get_total_page(total_posts):
    post_per_page = 10
    
    if total_posts % post_per_page == 0:
        last_page = total_posts//post_per_page
    else:
        last_page = (total_posts//post_per_page) + 1

    return last_page            

@app.route('/')
def main():
    topics_from_db = []
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT COUNT(*) as total_posts FROM topic "
            cursor.execute(sql)
            total_posts = int(cursor.fetchone()['total_posts'])
            last_page = get_total_page(total_posts)
            page = request.args.get('page', 1, type=int)
            offset = (page-1) * 10

            sql_post = "SELECT * FROM topic ORDER BY id DESC LIMIT %s OFFSET %s"
            cursor.execute(sql_post, (10, offset))
            topics_from_db = cursor.fetchall()

    except Exception as e:
        print(f"데이터베이스 조회 오류: {e}")
        topics_from_db = []
        page, last_page = 1, 1

    finally:
        if conn:
            conn.close()

    return render_template('base.html', topics=topics_from_db, current_page=page, last_page = last_page)

@app.route("/register", methods = ['GET', 'POST'])
def register():
    conn = None
    
    try:
        if request.method == 'GET':
            return render_template('register.html')

        if request.method == 'POST':
            user_id = request.form['user_id']
            user_ps = request.form['user_ps']
            user_name = request.form['user_name']
            user_school = request.form['user_school']
        
        hashed_ps = generate_password_hash(user_ps)
        conn = get_db_connection()
        
        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE user_id = %s"
            cursor.execute(sql, (user_id))
            current_user = cursor.fetchone()

            if current_user:
                flash('이미 존재하는 ID입니다!')
                return redirect(url_for('register'))
            else:
                with conn.cursor() as cursor:
                    sql = "INSERT INTO users (user_id, user_ps, user_name, user_school) VALUES (%s, %s, %s, %s)"
                    cursor.execute(sql, (user_id, hashed_ps, user_name, user_school))
                    conn.commit()
                    flash('회원가입 성공! 로그인을 진행해주세요')
                    return redirect(url_for('main'))
        
    except Exception as e:
        print(f"데이터베이스 조회 오류: {e}")
        return "오류가 발생했습니다. <a href='/'>돌아가기</a>"
    
    finally:
        if conn:
            conn.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    conn = None

    if request.method == 'GET':
        return render_template('login.html')

    if request.method == 'POST':
        user_id = request.form['user_id']
        user_ps = request.form['user_ps']

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE user_id = %s"
            cursor.execute(sql, (user_id))
            current_user_info = cursor.fetchone()

        if current_user_info is None:
            return "존재하지 않는 사용자입니다. <a href='/'>돌아가기</a>"
        
    
        if check_password_hash(current_user_info['user_ps'], user_ps):
            session['logged_in'] = True
            session['user_id'] = current_user_info['user_id']
            session['user_name'] = current_user_info['user_name']
            flash('로그인에 성공했습니다.')
            return redirect(url_for('main'))
        else:
            flash('아이디 혹은 비밀번호가 일치하지 않습니다.')
            return redirect(url_for('main'))
        
    except Exception as e:
        print(f"데이터베이스 조회 오류: {e}")
        return "오류가 발생했습니다. <a href='/'>돌아가기</a>"
    
    finally:
        if conn:
            conn.close()

@app.route('/logout')
def logout():
    if session['logged_in'] == True:
        session.clear()
        flash('로그아웃 되었습니다.')
        return redirect(url_for('main'))
    
@app.route('/profile')
def profile():
    conn = None

    if 'logged_in' not in session:
        flash('로그인이 필요한 서비스입니다.')
        return redirect(url_for('main'))
    
    try:
        conn = get_db_connection()
        name = session['user_name']
        user_info = []
        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE user_id = %s"
            cursor.execute(sql, (name))
            user_info = cursor.fetchone()
            return render_template('profile.html', user=user_info)

    except Exception as e:
        print(f"데이터베이스 조회 오류: {e}")
        return "오류가 발생했습니다. <a href='/'>돌아가기</a>"
    
    finally:
        if conn:
            conn.close()    


@app.route('/read/<int:id>/')
def read(id):
    conn = None

    if 'logged_in' not in session:
        flash('로그인이 필요한 서비스입니다.')
        return redirect(url_for('main'))
    
    try:
        conn = get_db_connection()

        with conn.cursor() as cursor:
            sql = "SELECT * FROM topic WHERE id = %s"
            cursor.execute(sql, (id,))
            topic = cursor.fetchone() 

        if topic is None:
            return "존재하지 않는 게시글입니다. <a href='/'>돌아가기</a>"

        return render_template('read.html',topic=topic)

    except Exception as e:
        print(f"데이터베이스 조회 오류: {e}")
        return "오류가 발생했습니다. <a href='/'>돌아가기</a>"
    
    finally:
        if conn:
            conn.close()

@app.route('/create/', methods=['GET', 'POST'])
def create():
    conn = None
    if 'logged_in' not in session:
        flash('로그인이 필요한 서비스입니다.')
        return redirect(url_for('main'))
    try:
        conn = get_db_connection()
        
        if request.method == 'POST':
            title = request.form['title']
            body = request.form['body']
            
            with conn.cursor() as cursor:
                sql = "INSERT INTO topic (title, body) VALUES (%s, %s)"
                cursor.execute(sql, (title, body))
                conn.commit()
                new_id = cursor.lastrowid
                return redirect(f'/read/{new_id}/')

        else: # request.method == 'GET'
            return render_template('create.html')

    except Exception as e:
        print(f"데이터 처리 오류: {e}")
        return "오류가 발생했습니다. <a href='/'>돌아가기</a>"
    
    finally:
        if conn:
            conn.close() 

@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    conn = None
    if 'logged_in' not in session:
        flash('로그인이 필요한 서비스입니다.')
        return redirect(url_for('main'))
    try:
        conn = get_db_connection()
        
        if request.method == 'POST':
            title = request.form['title']
            body = request.form['body']

            with conn.cursor() as cursor:
                sql = "UPDATE topic SET title=%s, body=%s WHERE id=%s"
                cursor.execute(sql, (title, body, id))
                conn.commit()
                return redirect(f'/read/{id}/')

        else:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM topic WHERE id = %s"
                cursor.execute(sql, (id,))
                topic = cursor.fetchone()

            if topic is None:
                return "존재하지 않는 게시글입니다. <a href='/'>돌아가기</a>"

            return render_template('update.html', topic=topic)
            
    except Exception as e:
        print(f"데이터 처리 오류: {e}")
        return "오류가 발생했습니다. <a href='/'>돌아가기</a>"
    finally:
        if conn:
            conn.close()
   
@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    conn = None
    if 'logged_in' not in session:
        flash('로그인이 필요한 서비스입니다.')
        return redirect(url_for('main'))
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "DELETE FROM topic WHERE id = %s"
            cursor.execute(sql, (id,))
            conn.commit()
            return redirect('/')
    
    except Exception as e:
        print(f"데이터 처리 오류: {e}")
        return "오류가 발생했습니다. <a href='/'>돌아가기</a>"
    
    finally:
        if conn:
            conn.close()

@app.route('/search/', methods=['GET'])
def search():
    
    topics_from_db = []
    search_name = request.args.get('search_name')
    search_type = request.args.get('search_menu')

    if not search_name or not search_name.strip():
        return render_template('search.html', topics=[])
    
    conn = None
    try:
        if search_type == 'title':
            conn = get_db_connection()
            with conn.cursor() as cursor:
                sql = "SELECT * FROM topic WHERE title LIKE %s ORDER BY id DESC"
                cursor.execute(sql, f"%{search_name}%")                    
                topics_from_db = cursor.fetchall()
                return render_template('search.html', things = topics_from_db, search_name = search_name)
            
        elif search_type == 'body':
            conn = get_db_connection()
            with conn.cursor() as cursor:
                sql = "SELECT * FROM topic WHERE body LIKE %s ORDER BY id DESC"
                cursor.execute(sql, f"%{search_name}%")
                topics_from_db = cursor.fetchall()
                return render_template('search.html', things = topics_from_db, search_name = search_name)
            
        elif search_type == 'title_body':
            conn = get_db_connection()
            with conn.cursor() as cursor:
                sql= "SELECT * FROM topic WHERE title LIKE %s OR body LIKE %s ORDER BY id DESC"
                cursor.execute(sql, (f"%{search_name}%", f"%{search_name}%"))
                topics_from_db = cursor.fetchall()
                return render_template('search.html', things = topics_from_db, search_name = search_name)
        else:
            return render_template('search.html', error="잘못된 검색 유형입니다.")
        
    except Exception as e:
        print(f"데이터베이스 조회 오류: {e}")
        return render_template('search.html', error=f"데이터베이스 오류: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)