"""Stable error codes shared by the JSON CLI and future HTTP adapter."""


class ProjectError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.details = details or {}

    def to_dict(self):
        return {"code": self.code, "message": str(self), "details": self.details}
