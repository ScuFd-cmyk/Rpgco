"""Domain errors raised by services and mapped to HTTP codes in main.py."""


class GameError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidAction(GameError):
    status_code = 400


class Unauthorized(GameError):
    status_code = 401


class Forbidden(GameError):
    status_code = 403


class NotFound(GameError):
    status_code = 404


class Conflict(GameError):
    """Raised for duplicates and stale (version-mismatched) updates."""
    status_code = 409
