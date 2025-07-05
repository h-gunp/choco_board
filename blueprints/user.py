from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import pymysql
import os

user_bp = Blueprint('user', __name__)

db_config = None
upload_folder = None

ALLOWED_EXTENTIONS = {'png', 'jpg', 'jpeg'}
ALLOWED_MIMETYPES = {'image/png', 'image/jpg', 'image/jpeg'}
MAX_FILE_SIZE = 30*1024*1024

def file_allow(filename, mimetype):
    if filename not in ALLOWED_EXTENTIONS and '.':
        return False
    if mimetype not in ALLOWED_MIMETYPES:
        return False
    
    return True

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
                    return redirect(url_for('topic.create'))                                                   
                                                                                                    
            if len(profile_image.read()) > MAX_FILE_SIZE:                                                              
                    flash('최대 30MB까지 허용됩니다.')                                
                    return redirect(url_for('topic.create'))                                                   
            profile_image.seek(0)
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
