from flask import Blueprint, request, render_template, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
import pymysql
import os

topic_bp = Blueprint('topic', __name__)

db_config = None
upload_folder = None

ALLOWED_EXTENTIONS = ('txt', 'png', 'jpg', 'jpeg')
ALLOWED_MIMETYPES = ('text/plain', 'image/png', 'image/jpg', 'image/jpeg')
MAX_FILE_SIZE = 30*1024*1024

def file_allow(filename, mimetype):
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENTIONS and
            mimetype in ALLOWED_MIMETYPES)

def get_db_connection():
    return pymysql.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        db=db_config['db'],
        charset=db_config['charset'],
        cursorclass=pymysql.cursors.DictCursor
    )

@topic_bp.route('/read/<int:id>/', methods=['GET', 'POST'])
def read(id):
    if 'logged_in' not in session:
        flash('로그인이 필요한 서비스입니다.')
        return redirect(url_for('auth.login'))
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT * FROM topic WHERE id = %s"
            cursor.execute(sql, (id,))
            topic = cursor.fetchone()

        if topic is None:
            flash('존재하지 않는 게시글입니다.')
            return redirect(url_for('main.main'))
        
        file_info = None
        with conn.cursor() as cursor:
            sql="SELECT topic_id, file_name, file_path FROM files WHERE topic_id = %s"
            cursor.execute(sql, (id,))
            file_info = cursor.fetchone()

        if topic['is_secret'] == 1:
            if request.method == 'POST':
                post_ps = request.form.get('secret_key')
                if post_ps == topic['secret_key']:
                    session[f'topic_{id}_access'] = True
                else:
                    flash('비밀번호가 틀립니다.')
                    return redirect(url_for('main.main'))
            
            if not session.get(f'topic_{id}_access') and topic['post_user_id'] != session.get('user_id'):
                return render_template('read_secret.html', topic=topic)
    
        return render_template('read.html', topic=topic, file=file_info)

    except Exception as e:
        print(f"데이터베이스 조회 오류: {e}")
        flash('오류가 발생했습니다.')
        return redirect(url_for('main.main'))
    
    finally:
        if conn:
            conn.close()

@topic_bp.route('/create/', methods=['GET', 'POST'])
def create():
    if 'logged_in' not in session:
        flash('로그인이 필요한 서비스입니다.')
        return redirect(url_for('auth.login'))
    
    if request.method == 'GET':
        return render_template('create.html')

    conn = None
    try:
        conn = get_db_connection()
        title = request.form['title']
        body = request.form['body']
        is_secret = 1 if 'is_secret' in request.form else 0
        secret_key = request.form.get('secret_key')
        user_id = session['user_id']
        user_name = session['user_name']

        with conn.cursor() as cursor:
            sql = "INSERT INTO topic (title, body, post_user_id, post_user_name, is_secret, secret_key) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, (title, body, user_id, user_name, is_secret, secret_key))
            new_id = cursor.lastrowid

            if 'file' in request.files and request.files['file'].filename != '':
                f = request.files['file']
                if not file_allow(f.filename, f.mimetype):                                                   
                    flash('허용되지 않는 파일 형식입니다.')                                                    
                    return redirect(url_for('topic.create'))                                                   
                                                                                                    
                if len(f.read()) > MAX_FILE_SIZE:                                                              
                    flash('최대 30MB까지 허용됩니다.')                                
                    return redirect(url_for('topic.create'))                                                   
                f.seek(0)

                filename = secure_filename(f.filename)
                filepath = os.path.join(upload_folder, filename)
                f.save(filepath)
            
                sql_file = "INSERT INTO files (topic_id, file_name, file_path) VALUES (%s, %s, %s)"
                cursor.execute(sql_file, (new_id, filename, filepath))

            conn.commit()
            return redirect(url_for('topic.read', id=new_id))

    except Exception as e:
        print(f"데이터 처리 오류: {e}")
        if conn:
            conn.rollback()
        flash('게시글 작성 중 오류가 발생했습니다.')
        return redirect(url_for('main.main'))
    
    finally:
        if conn:
            conn.close()

@topic_bp.route('/download/<int:topic_id>')
def download(topic_id):
    if 'logged_in' not in session:
        flash('로그인이 필요한 서비스입니다.')
        return redirect(url_for('auth.login'))
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT file_name, file_path FROM files WHERE topic_id = %s"
            cursor.execute(sql, (topic_id,))
            file_info = cursor.fetchone()

        if file_info:
            file_name = file_info['file_name']
            directory = os.path.dirname(file_info['file_path'])
            return send_from_directory(directory, file_name, as_attachment=True)
        else:
            flash('파일을 찾을 수 없습니다.')
            return redirect(url_for('main.main'))

    except Exception as e:
        print(f"파일 다운로드 오류: {e}")
        flash('파일 다운로드 중 오류가 발생했습니다.')
        return redirect(url_for('main.main'))
    
    finally:
        if conn:
            conn.close()

@topic_bp.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    if 'logged_in' not in session:
        flash('로그인이 필요한 서비스입니다.')
        return redirect(url_for('auth.login'))
    
    conn = None
    try:
        conn = get_db_connection()
        user_id = session.get('user_id')

        with conn.cursor() as cursor:
            sql = "SELECT * FROM topic WHERE id = %s"
            cursor.execute(sql, (id,))
            topic = cursor.fetchone()

        if topic is None:
            flash('존재하지 않는 게시글입니다.')
            return redirect(url_for('main.main'))

        if topic['post_user_id'] != user_id:
            flash('수정 권한이 없습니다.')
            return redirect(url_for('main.main'))

        if request.method == 'POST':
            title = request.form['title']
            body = request.form['body']

            with conn.cursor() as cursor:
                sql = "UPDATE topic SET title=%s, body=%s WHERE id=%s"
                cursor.execute(sql, (title, body, id))

            if 'file' in request.files and request.files['file'].filename != '':
                new_file = request.files['file']
                if not file_allow(new_file.filename, new_file.mimetype):                                                   
                    flash('허용되지 않는 파일 형식입니다.')                                                    
                    return redirect(url_for('topic.create'))                                                   
                                                                                                    
                if len(new_file.read()) > MAX_FILE_SIZE:                                                              
                    flash('최대 30MB까지 허용됩니다.')                                
                    return redirect(url_for('topic.create'))                                                   
                new_file.seek(0)
                filename = secure_filename(new_file.filename)
                filepath = os.path.join(upload_folder, filename)
                
                new_file.save(filepath)

                with conn.cursor() as cursor:
                    sql = "SELECT file_name FROM files WHERE topic_id=%s"
                    cursor.execute(sql, (id,))
                    old_file = cursor.fetchone()
                    if old_file:
                        old_file_path = os.path.join(upload_folder, old_file['file_name'])
                        if os.path.exists(old_file_path):
                            os.remove(old_file_path)
                        
                        sql_delete = "DELETE FROM files WHERE topic_id=%s"
                        cursor.execute(sql_delete, (id,))

                with conn.cursor() as cursor:
                    sql = "INSERT INTO files (topic_id, file_name, file_path) VALUES (%s, %s, %s)"
                    cursor.execute(sql, (id, filename, filepath))
            
            conn.commit()
            return redirect(url_for('topic.read', id=id))
            
        else:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM files WHERE topic_id=%s"
                cursor.execute(sql, (id,))
                file_info = cursor.fetchone()
            return render_template('update.html', topic=topic, file=file_info)
            
    except Exception as e:
        print(f"데이터 처리 오류: {e}")
        if conn:
            conn.rollback()
        flash('게시글 수정 중 오류가 발생했습니다.')
        return redirect(url_for('main.main'))
    finally:
        if conn:
            conn.close()

@topic_bp.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    if 'logged_in' not in session:
        flash('로그인이 필요한 서비스입니다.')
        return redirect(url_for('auth.login'))

    conn = None
    try:
        conn = get_db_connection()
        user_id = session.get('user_id')

        with conn.cursor() as cursor:
            sql = "SELECT post_user_id FROM topic WHERE id = %s"
            cursor.execute(sql, (id,))
            topic = cursor.fetchone()

        if topic is None:
            flash('존재하지 않는 게시글입니다.')
            return redirect(url_for('main.main'))

        if topic['post_user_id'] != user_id:
            flash('삭제 권한이 없습니다.')
            return redirect(url_for('main.main'))

        with conn.cursor() as cursor:
            sql = "SELECT file_name FROM files WHERE topic_id = %s"
            cursor.execute(sql, (id,))
            file_to_delete = cursor.fetchone()

            if file_to_delete:
                file_path = os.path.join(upload_folder, file_to_delete['file_name'])
                if os.path.exists(file_path):
                    os.remove(file_path)

        with conn.cursor() as cursor:
            sql = "DELETE FROM topic WHERE id = %s"
            cursor.execute(sql, (id,))
        
        conn.commit()
        flash('게시글이 성공적으로 삭제되었습니다.')
        return redirect(url_for('main.main'))

    except Exception as e:
        print(f"데이터 처리 오류: {e}")
        if conn:
            conn.rollback()
        flash('오류가 발생하여 삭제에 실패했습니다.')
        return redirect(url_for('main.main'))
    
    finally:
        if conn:
            conn.close()

@topic_bp.route('/search/', methods=['GET'])
def search():
    search_name = request.args.get('search_name')
    search_type = request.args.get('search_menu')

    if not search_name or not search_name.strip():
        return render_template('search.html', topics=[])
    
    conn = None
    try:
        conn = get_db_connection()
        query = f"%{search_name}%"
        
        if search_type == 'title':
            sql = "SELECT * FROM topic WHERE title LIKE %s ORDER BY id DESC"
            params = (query,)
        elif search_type == 'body':
            sql = "SELECT * FROM topic WHERE body LIKE %s ORDER BY id DESC"
            params = (query,)
        elif search_type == 'title_body':
            sql = "SELECT * FROM topic WHERE title LIKE %s OR body LIKE %s ORDER BY id DESC"
            params = (query, query)
        else:
            return render_template('search.html', error="잘못된 검색 유형입니다.")

        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            topics_from_db = cursor.fetchall()
        
        return render_template('search.html', things=topics_from_db, search_name=search_name)
        
    except Exception as e:
        print(f"데이터베이스 조회 오류: {e}")
        return render_template('search.html', error=f"데이터베이스 오류: {e}")
    finally:
        if conn:
            conn.close()
