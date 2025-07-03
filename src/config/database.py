import os
import psycopg2
from psycopg2.extras import RealDictCursor
from supabase import create_client, Client

# Simple Supabase client for basic operations
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(url, key)

class DatabaseConfig:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        self.supabase_service_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.database_url = os.getenv('DATABASE_URL')
        
        # Initialize Supabase client
        self.supabase: Client = create_client(self.supabase_url, self.supabase_service_key)
    
    def get_db_connection(self):
        """Get a direct PostgreSQL connection for complex queries"""
        try:
            conn = psycopg2.connect(
                self.database_url,
                cursor_factory=RealDictCursor
            )
            return conn
        except Exception as e:
            print(f"Database connection error: {e}")
            return None
    
    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        conn = self.get_db_connection()
        if not conn:
            return None
        
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                if query.strip().upper().startswith('SELECT'):
                    return cursor.fetchall()
                else:
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            conn.rollback()
            print(f"Query execution error: {e}")
            return None
        finally:
            conn.close()

# Global database instance
db_config = DatabaseConfig()
