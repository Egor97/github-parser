import os


class Settings:
    API_TOKEN: str = str(os.environ.get('API_GITHUB_TOKEN'))
    DB_USER: str = str(os.environ.get('DB_USER'))
    DB_PASS: str = str(os.environ.get('DB_PASS'))
    DB_HOST: str = str(os.environ.get('DB_HOST'))
    DB_PORT: int = int(os.environ.get('DB_PORT'))
    DB_NAME: str = str(os.environ.get('DB_NAME'))


settings = Settings()
