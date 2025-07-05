from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
import pymysql
import os

auth_bp = Blueprint('auth', __name__)

db_config = None
mail = None

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

def generate_code():
    import random
    return str(random.randint(100000, 999999))

@auth_bp.route("/register", methods=['GET', 'POST'])
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
            user_mail = request.form['user_mail']

            if " " in user_id or " " in user_ps:
                flash('아이디와 패스워드에 공백이 포함되면 안됩니다.')
                return redirect(url_for('auth.register'))

            hashed_ps = generate_password_hash(user_ps)
            conn = get_db_connection()

            with conn.cursor() as cursor:
                sql = "SELECT * FROM users WHERE user_id = %s"
                cursor.execute(sql, (user_id,))
                current_user = cursor.fetchone()

                if current_user:
                    flash('이미 존재하는 ID입니다!')
                    return redirect(url_for('auth.register'))
                else:
                    sql = "INSERT INTO users (user_id, user_ps, user_name, user_school, user_mail) VALUES (%s, %s, %s, %s, %s)"
                    cursor.execute(sql, (user_id, hashed_ps, user_name, user_school, user_mail))
                    conn.commit()
                    flash('회원가입 성공! 로그인을 진행해주세요')
                    return redirect(url_for('main.main'))

    except Exception as e:
        print(f"데이터베이스 조회 오류: {e}")
        return "오류가 발생했습니다. <a href='/'>돌아가기</a>"

    finally:
        if conn:
            conn.close()

@auth_bp.route('/login', methods=['GET', 'POST'])
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
                cursor.execute(sql, (user_id,))
                current_user_info = cursor.fetchone()

            if current_user_info is None:
                flash("존재하지 않는 사용자입니다.")
                return redirect(url_for('auth.login'))

            if check_password_hash(current_user_info['user_ps'], user_ps):
                session.clear()
                session['logged_in'] = True
                session['user_id'] = current_user_info['user_id']
                session['user_name'] = current_user_info['user_name']
                flash('로그인에 성공했습니다.')
                return redirect(url_for('main.main'))
            else:
                flash('아이디 혹은 비밀번호가 올바르지 않습니다.')
                return redirect(url_for('auth.login'))

        except Exception as e:
            print(f"데이터베이스 조회 오류: {e}")
            return "오류가 발생했습니다. <a href='/'>돌아가기</a>"

        finally:
            if conn:
                conn.close()

@auth_bp.route('/logout')
def logout():
    if 'logged_in' in session:
        session.clear()
        flash('로그아웃 되었습니다.')
    return redirect(url_for('main.main'))

@auth_bp.route('/find_account', methods=['GET', 'POST'])
def find_account():
    if request.method == 'GET':
        return render_template('find_account.html')

    conn = None
    try:
        user_name = request.form['user_name']
        user_school = request.form['user_school']
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE user_name = %s AND user_school = %s"
            cursor.execute(sql, (user_name, user_school,))
            user_info = cursor.fetchone()

            if user_info is None:
                flash('존재하지 않는 사용자 정보입니다.')
                return redirect(url_for('auth.find_account'))
            else:
                return render_template('find_account.html', user=user_info)

    except Exception as e:
        print(f"데이터베이스 조회 오류: {e}")
        flash('사용자 정보를 찾는 중 오류가 발생했습니다.')
        return redirect(url_for('main.main'))

    finally:
        if conn:
            conn.close()

@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    conn = None
    if request.method == 'GET':
        return render_template('reset_password.html')
    
    try:
        user_id = request.form['id']
        user_name = request.form['name']
        user_email = request.form['mail']

        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE user_id=%s AND user_name=%s AND user_mail=%s"
            cursor.execute(sql, (user_id, user_name, user_email,))
            user_info = cursor.fetchone()

            if user_info is None:
                flash('존재하지 않는 사용자입니다.')
                return redirect(url_for('auth.reset_password'))
            else:
                verification_code = generate_code()
                session['verification_code'] = verification_code
                session['mail'] = user_email

                msg = Message(
                    subject="초코파이 인사이드 이메일 인증 코드입니다.",
                    recipients=[user_email],
                    body=f"요청하신 인증 코드는 [{verification_code}] 입니다."
                )
                mail.send(msg)
                flash('이메일로 인증 코드를 발송했습니다.')
                return redirect(url_for('auth.verify'))

    except Exception as e:
        print(f"오류: {e}")
        flash('오류가 발생했습니다.')
        return redirect(url_for('auth.reset_password'))
    
    finally:
        if conn:
            conn.close()

@auth_bp.route('/verify', methods=['GET', 'POST'])
def verify():
    if 'verification_code' not in session:
        return redirect(url_for('auth.reset_password'))

    if request.method == 'GET':
        return render_template('verify.html', mail=session.get('mail'))

    conn = None
    try:
        user_mail = session.get('mail')
        user_code = request.form['code']

        if user_code == session['verification_code']:
            new_password = generate_code()
            hashed_password = generate_password_hash(new_password)
            
            conn = get_db_connection()
            with conn.cursor() as cursor:
                sql = "UPDATE users SET user_ps=%s WHERE user_mail=%s"
                cursor.execute(sql, (hashed_password, user_mail,))
                conn.commit()

            session.pop('verification_code', None)
            session.pop('mail', None)
            flash(f'비밀번호가 성공적으로 초기화되었습니다! 임시 비밀번호는 {new_password} 입니다.')
            return redirect(url_for('auth.login'))
        else:
            flash('인증 코드가 올바르지 않습니다.')
            return render_template('verify.html', mail=session.get('mail'))

    except Exception as e:
        print(f"오류: {e}")
        flash('오류가 발생했습니다.')
        return redirect(url_for('auth.reset_password'))
    
    finally:
        if conn:
            conn.close()

@auth_bp.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'logged_in' not in session:
        flash('로그인이 필요한 서비스입니다.')
        return redirect(url_for('auth.login'))

    if request.method == 'GET':
        return render_template('change_password.html')

    conn = None
    try:
        user_id = session.get('user_id')
        old_ps = request.form.get('old_ps')
        new_ps = request.form.get('new_ps')
        re_new_ps = request.form.get('re_new_ps')

        if new_ps != re_new_ps:
            flash('새 비밀번호가 일치하지 않습니다.')
            return redirect(url_for('auth.change_password'))
        
        if " " in new_ps:
            flash('패스워드에 공백이 포함되면 안됩니다.')
            return redirect(url_for('auth.change_password'))

        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT user_ps FROM users WHERE user_id=%s"
            cursor.execute(sql, (user_id,))
            user_info = cursor.fetchone()

        if not user_info or not check_password_hash(user_info['user_ps'], old_ps):
            flash('현재 비밀번호가 올바르지 않습니다.')
            return redirect(url_for('auth.change_password'))

        hashed_password = generate_password_hash(new_ps)
        with conn.cursor() as cursor:
            sql = "UPDATE users SET user_ps=%s WHERE user_id=%s"
            cursor.execute(sql, (hashed_password, user_id,))
            conn.commit()
        
        flash('비밀번호 변경이 완료되었습니다. 다시 로그인해주세요.')
        return redirect(url_for('auth.logout'))

    except Exception as e:
        print(f"데이터베이스 오류: {e}")
        flash('데이터베이스 처리 중 오류가 발생했습니다.')
        return redirect(url_for('main.main'))
    
    finally:
        if conn:
            conn.close()

