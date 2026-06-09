import os


class Config:
    SECRET_KEY = 'your-secret-key-change-this-in-production'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tasks.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    LOG_FILE = 'logs/app.log'
    LOG_MAX_BYTES = 10000
    LOG_BACKUP_COUNT = 3
