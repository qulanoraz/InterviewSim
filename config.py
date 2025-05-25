# Flask configuration settings will be here 

import os
from dotenv import load_dotenv

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    DEEPGRAM_API_KEY = os.environ.get('DEEPGRAM_API_KEY')
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
    APP_SITE_URL = os.environ.get('APP_SITE_URL') or 'http://localhost:5000'
    APP_NAME = os.environ.get('APP_NAME') or 'JobSim AI'
    # Add other global configurations here

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    # Development-specific configurations
    # For example, to use a local development database:
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
    #     'sqlite:///' + os.path.join(basedir, 'dev.db')


class TestingConfig(Config):
    TESTING = True
    # Testing-specific configurations
    # SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
    #     'sqlite:///' + os.path.join(basedir, 'test.db')
    WTF_CSRF_ENABLED = False # Often disabled for testing forms


class ProductionConfig(Config):
    DEBUG = False
    # Production-specific configurations
    # For example, to use a production database:
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    # Consider more robust logging, security headers, etc.

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 