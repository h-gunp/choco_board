from flask import Flask
from dotenv import load_dotenv
import os
import pymysql

from blueprints.main import main_bp
from blueprints.auth import auth_bp
from blueprints.topic import topic_bp
from blueprints.user import user_bp

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)

    db_password = os.getenv('DB_PASSWORD')
    mail_address = os.getenv('MAIL_ADRESS')
    mail_password = os.getenv('MAIL_PASSWORD')

    db_config = {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': db_password,
        'db': 'board',
        'charset': 'utf8mb4'
    }

    UPLOAD_FOLDER = 'static/uploads'
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = mail_address
    app.config['MAIL_PASSWORD'] = mail_password
    app.config['MAIL_DEFAULT_SENDER'] = ('초코파이 인사이드', mail_address)

    from flask_mail import Mail
    mail = Mail(app)

    from blueprints import auth, topic, user, main
    auth.db_config = db_config
    auth.mail = mail
    topic.db_config = db_config
    topic.upload_folder = app.config['UPLOAD_FOLDER']
    user.db_config = db_config
    user.upload_folder = app.config['UPLOAD_FOLDER']
    main.db_config = db_config

    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(topic_bp, url_prefix='/topic')
    app.register_blueprint(user_bp, url_prefix='/user')

    return app

def init_db(app):
    db_config = {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': os.getenv('DB_PASSWORD'),
        'db': 'board',
        'charset': 'utf8mb4'
    }
    
    conn = None
    try:
        server_conn_info = db_config.copy()
        db_name = server_conn_info.pop('db')
        conn = pymysql.connect(**server_conn_info)
        
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
            conn.select_db(db_name)

        with conn.cursor() as cursor:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS users (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_id VARCHAR(100) NOT NULL UNIQUE,
                user_ps VARCHAR(255) NOT NULL,
                user_name VARCHAR(100) NOT NULL,
                user_school VARCHAR(100),
                user_mail VARCHAR(100) UNIQUE,
                profile_image VARCHAR(255)
            )
            """
            cursor.execute(create_table_sql)

        with conn.cursor() as cursor:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS topic (
                id INT PRIMARY KEY AUTO_INCREMENT,
                title VARCHAR(255) NOT NULL,
                body TEXT NOT NULL,
                post_user_id VARCHAR(100) NOT NULL,
                post_user_name VARCHAR(100) NOT NULL,
                is_secret BOOLEAN,
                secret_key VARCHAR(100)
            )
            """
            cursor.execute(create_table_sql)

        with conn.cursor() as cursor:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS files (
                id INT PRIMARY KEY AUTO_INCREMENT,
                topic_id INT NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                file_path VARCHAR(255) NOT NULL,
                FOREIGN KEY (topic_id) REFERENCES topic(id) ON DELETE CASCADE
            )
            """
            cursor.execute(create_table_sql)
            
        conn.commit()    
        print("데이터베이스 초기화 완료.")

    except Exception as e:
        print(f"데이터베이스 초기화 오류: {e}")
            
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        init_db(app)
    app.run(debug=True)
