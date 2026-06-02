import sqlite3
import os
from datetime import datetime, timedelta

def init_db():
    conn = sqlite3.connect('sandogh.db')
    cursor = conn.cursor()
    
    # جدول وام‌ها با قابلیت ذخیره مسیر رسیدها و تاریخ تسویه
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            names TEXT,
            total_amount REAL,
            monthly_amount REAL,
            total_installments INTEGER,
            paid_count INTEGER DEFAULT 0,
            completion_date TEXT,
            receipts TEXT -- ذخیره مسیر عکس‌ها به صورت متن جدا شده با کاما
        )
    ''')
    conn.commit()
    conn.close()

# اجرای اولیه برای ساخت دیتابیس
if __name__ == "__main__":
    init_db()
    print("دیتابیس با موفقیت ایجاد شد.")