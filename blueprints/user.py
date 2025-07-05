from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
import os

user_bp = Blueprint('user', __name__)

db_config = None
upload_folder = None

ALLOWED_EXTENTIONS = ('png', 'jpg', 'jpeg')
ALLOWED_MIMETYPES = ('image/png', 'image/jpg', 'image/jpeg')
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

@user_bp.route('/profile/<user_name>')
def profile(user_name):
    if 'logged_in' not in session:
        flash('로그인이 필요한 서비스입니다.')
        return redirect(url_for('auth.login'))
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE user_name = %s"
            cursor.execute(sql, (user_name,))
            user_info = cursor.fetchone()

            if not user_info:
                flash('존재하지 않는 사용자입니다.')
                return redirect(url_for('main.main'))

            return render_template('profile.html', user=user_info)

    except Exception as e:
        print(f"데이터베이스 조회 오류: {e}")
        flash('오류가 발생했습니다.')
        return redirect(url_for('main.main'))
    
    finally:
        if conn:
            conn.close()

@user_bp.route('/delete_account', methods=['GET', 'POST'])
def delete_account():
    if 'logged_in' not in session:
        flash('로그인이 필요한 서비스입니다.')
        return redirect(url_for('auth.login'))

    conn = None
    try:
        conn = get_db_connection()
        user_id = session.get('user_id')

        if request.method == 'POST':
            password = request.form.get('password')

            with conn.cursor() as cursor:
                sql = "SELECT user_ps, profile_image FROM users WHERE user_id = %s"
                cursor.execute(sql, (user_id,))
                user_info = cursor.fetchone()

            if not user_info or not check_password_hash(user_info['user_ps'], password):
                flash('비밀번호가 올바르지 않습니다.')
                return render_template('delete_account.html')

            if user_info['profile_image']:
                profile_image_path = os.path.join(upload_folder, user_info['profile_image'])
                if os.path.exists(profile_image_path):
                    os.remove(profile_image_path)

            with conn.cursor() as cursor:
                sql_select_topic_files = "SELECT f.file_name FROM files f JOIN topic t ON f.topic_id = t.id WHERE t.post_user_id = %s"
                cursor.execute(sql_select_topic_files, (user_id,))
                topic_files = cursor.fetchall()
                for file_entry in topic_files:
                    file_path_to_delete = os.path.join(upload_folder, file_entry['file_name'])
                    if os.path.exists(file_path_to_delete):
                        os.remove(file_path_to_delete)

            with conn.cursor() as cursor:
                sql_delete_topics = "DELETE FROM topic WHERE post_user_id = %s"
                cursor.execute(sql_delete_topics, (user_id,))

            with conn.cursor() as cursor:
                sql_delete_user = "DELETE FROM users WHERE user_id = %s"
                cursor.execute(sql_delete_user, (user_id,))
            
            conn.commit()
            session.clear()
            flash('회원 탈퇴가 성공적으로 완료되었습니다.')
            return redirect(url_for('main.main'))

        return render_template('delete_account.html')

    except Exception as e:
        print(f"회원 탈퇴 오류: {e}")
        if conn:
            conn.rollback()
        flash('회원 탈퇴 중 오류가 발생했습니다.')
        return redirect(url_for('main.main'))
    finally:
        if conn:
            conn.close()

@user_bp.route('/profile/edit', methods=['GET', 'POST'])
def profileEdit():
    if 'logged_in' not in session:
        flash('로그인이 필요한 서비스입니다.')
        return redirect(url_for('auth.login'))

    conn = None
    try:
        conn = get_db_connection()
        user_id = session['user_id']

        if request.method == 'GET':
            with conn.cursor() as cursor:
                sql = "SELECT * FROM users WHERE user_id=%s"
                cursor.execute(sql, (user_id,))
                user_info = cursor.fetchone()
                return render_template('profileEdit.html', user=user_info)
        
        user_name = request.form['user_name']   
        user_school = request.form['user_school']
        profile_image = request.files.get('profile_image')
        
        image_filename_to_save = None
        if profile_image and profile_image.filename:
            if not file_allow(profile_image.filename, profile_image.mimetype):                                                   
                    flash('허용되지 않는 파일 형식입니다.')                                                    
                    return redirect(url_for('user.profileEdit'))                                                   
                                                                                                    
            profile_image.seek(0, os.SEEK_END)
            file_size = profile_image.tell()
            profile_image.seek(0)

            if file_size > MAX_FILE_SIZE:                                                              
                    flash('최대 30MB까지 허용됩니다.')                                
                    return redirect(url_for('user.profileEdit'))                                                   
            
            image_filename = secure_filename(f"profile_{user_id}_{profile_image.filename}")
            new_image_path = os.path.join(upload_folder, image_filename)
            profile_image.save(new_image_path)
            image_filename_to_save = image_filename
            with conn.cursor() as cursor:
                sql = "SELECT profile_image FROM users WHERE user_id=%s"
                cursor.execute(sql, (user_id,))
                old_image = cursor.fetchone()
                if old_image and old_image['profile_image']:
                    old_image_path = os.path.join(upload_folder, old_image['profile_image'])
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)

        with conn.cursor() as cursor:
            if image_filename_to_save:
                sql = "UPDATE users SET user_name=%s, user_school=%s, profile_image=%s WHERE user_id=%s"
                cursor.execute(sql, (user_name, user_school, image_filename_to_save, user_id))
            else:
                sql = "UPDATE users SET user_name=%s, user_school=%s WHERE user_id=%s"
                cursor.execute(sql, (user_name, user_school, user_id))
            conn.commit()

        session['user_name'] = user_name
        flash('프로필이 성공적으로 수정되었습니다.')
        return redirect(url_for('user.profile', user_name=user_name))

    except Exception as e:
        print(f"데이터베이스 처리 오류: {e}")
        if conn:
            conn.rollback()
        flash('프로필 수정 중 오류가 발생했습니다.')
        return redirect(url_for('user.profile', user_name=session['user_name']))
    
    finally:
        if conn:
            conn.close()
