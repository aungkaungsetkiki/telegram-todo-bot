import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

def create_tables():
    """Create tables with DATE instead of TIMESTAMP"""
    commands = (
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username VARCHAR(255),
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            created_at DATE DEFAULT CURRENT_DATE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS tasks (
            task_id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id),
            title VARCHAR(255) NOT NULL,
            description TEXT,
            due_date DATE,
            completed BOOLEAN DEFAULT FALSE,
            created_at DATE DEFAULT CURRENT_DATE,
            updated_at DATE DEFAULT CURRENT_DATE
        )
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)
        """
    )
    
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        for command in commands:
            cur.execute(command)
        
        cur.close()
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

def get_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)

# Initialize tables on import
create_tables()
