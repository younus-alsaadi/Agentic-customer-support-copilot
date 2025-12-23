from src.helpers.config import get_settings, Settings


class BaseDataModel:
    def __init__(self, db_client: object) -> None:
        self.db_client = db_client
        self.app_settings = get_settings()
