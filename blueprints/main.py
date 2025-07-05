from flask import Blueprint, request, render_template
import pymysql

main_bp = Blueprint('main', __name__)

db_config = None

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

def get_total_page(total_posts):
    post_per_page = 10
    if total_posts % post_per_page == 0:
        return total_posts // post_per_page
    else:
        return (total_posts // post_per_page) + 1

@main_bp.route('/')
def main():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT COUNT(*) as total_posts FROM topic"
            cursor.execute(sql)
            total_posts = int(cursor.fetchone()['total_posts'])
            last_page = get_total_page(total_posts)
            page = request.args.get('page', 1, type=int)
            offset = (page - 1) * 10

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

    return render_template('base.html', topics=topics_from_db, current_page=page, last_page=last_page)
