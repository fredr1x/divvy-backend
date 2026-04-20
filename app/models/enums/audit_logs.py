from enum import Enum

class ActionType(str, Enum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    REFRESH_TOKEN = "REFRESH_TOKEN"
    LOGOUT = "LOGOUT"
    REGISTER = "REGISTER"


class ActionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ERROR = "ERROR"
