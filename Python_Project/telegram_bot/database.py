import sqlite3
from datetime import datetime
import config


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(config.DATABASE_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Создание таблиц"""
        # Пользователи бота
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Файлы (ХАБ)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS server (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                original_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                uploaded_by INTEGER,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (uploaded_by) REFERENCES users(user_id)
            )
        ''')

        # Логи операций
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                operation_type TEXT,
                file_id INTEGER,
                description TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (file_id) REFERENCES server(id)
            )
        ''')

        # Зарегистрированные устройства
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS registered_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active INTEGER DEFAULT 1
            )
        ''')

        self.conn.commit()

    # Методы пользователей
    def add_user(self, user_id, username, first_name, last_name):
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка добавления пользователя: {e}")
            return False

    def get_user_count(self):
        self.cursor.execute('SELECT COUNT(*) FROM users')
        return self.cursor.fetchone()[0]

    # Методы файлов
    def add_file(self, filename, original_name, file_type, file_path, file_size, uploaded_by):
        try:
            self.cursor.execute('''
                INSERT INTO server (filename, original_name, file_type, file_path, file_size, uploaded_by)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (filename, original_name, file_type, file_path, file_size, uploaded_by))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"Ошибка добавления файла: {e}")
            return None

    def get_files_by_type(self, file_type):
        self.cursor.execute('''
            SELECT id, filename, original_name, file_size, upload_date 
            FROM server WHERE file_type = ?
            ORDER BY upload_date DESC
        ''', (file_type,))
        return self.cursor.fetchall()

    def get_file_by_id(self, file_id):
        self.cursor.execute('SELECT * FROM server WHERE id = ?', (file_id,))
        return self.cursor.fetchone()

    def rename_file(self, file_id, new_name):
        try:
            self.cursor.execute('UPDATE server SET filename = ? WHERE id = ?', (new_name, file_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка переименования: {e}")
            return False

    def delete_file(self, file_id):
        try:
            self.cursor.execute('DELETE FROM server WHERE id = ?', (file_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка удаления: {e}")
            return False

    def log_operation(self, user_id, operation_type, file_id, description):
        try:
            self.cursor.execute('''
                INSERT INTO operations (user_id, operation_type, file_id, description)
                VALUES (?, ?, ?, ?)
            ''', (user_id, operation_type, file_id, description))
            self.conn.commit()
        except Exception as e:
            print(f"Ошибка логирования: {e}")

    # Методы устройств
    def register_device(self, token: str, ip_address: str, user_agent: str) -> bool:
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO registered_devices (token, ip_address, user_agent)
                VALUES (?, ?, ?)
            ''', (token, ip_address, user_agent))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка регистрации устройства: {e}")
            return False

    def check_device(self, token: str) -> bool:
        try:
            self.cursor.execute('''
                SELECT active FROM registered_devices WHERE token = ? AND active = 1
            ''', (token,))
            result = self.cursor.fetchone()
            if result:
                self.cursor.execute('''
                    UPDATE registered_devices SET last_seen = CURRENT_TIMESTAMP WHERE token = ?
                ''', (token,))
                self.conn.commit()
                return True
            return False
        except Exception as e:
            print(f"Ошибка проверки устройства: {e}")
            return False

    def get_all_devices(self):
        self.cursor.execute('''
            SELECT id, token, ip_address, user_agent, registered_at, last_seen, active
            FROM registered_devices
            ORDER BY last_seen DESC
        ''')
        return self.cursor.fetchall()

    def deactivate_device(self, device_id: int) -> bool:
        try:
            self.cursor.execute('''
                UPDATE registered_devices SET active = 0 WHERE id = ?
            ''', (device_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка деактивации устройства: {e}")
            return False

    def activate_device(self, device_id: int) -> bool:
        try:
            self.cursor.execute('''
                UPDATE registered_devices SET active = 1 WHERE id = ?
            ''', (device_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка активации устройства: {e}")
            return False

    def close(self):
        self.conn.close()


# Глобальный экземпляр БД
db = Database()