"""Config for flask app"""


class BaseConfig:
    SECRET_KEY = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

    @staticmethod
    def init_app(app):
        pass


class ProductionConfig(BaseConfig):
    DEBUG = False

    MONGODB_SETTINGS = {
        'db': 'blog',
        'host': '127.0.0.1',
        'port': 27017
    }


class DevelopmentConfig(BaseConfig):
    DEBUG = True

    # MONGO DB SETTINGS
    MONGODB_SETTINGS = {
        'db': 'blog',
        'host': '127.0.0.1',
        'port': 27017
    }


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig

}
