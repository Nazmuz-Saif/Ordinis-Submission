from rest_framework.views import exception_handler
from rest_framework.response import Response


class OrdinisException(Exception):
    """
    Base exception for all custom business-logic errors in Ordinis.
    Every app-specific exception should inherit from this.
    """
    code = "GENERIC_ERROR"
    message = "Something went wrong."
    status_code = 400

    def __init__(self, message=None, code=None):
        self.message = message or self.message
        self.code = code or self.code
        super().__init__(self.message)


def custom_exception_handler(exc, context):
    """
    Wraps DRF's default exception handler to always return our
    standard response envelope: { success, data, message } or
    { success, error: { code, message, field_errors } }.
    """
    response = exception_handler(exc, context)

    if isinstance(exc, OrdinisException):
        return Response(
            {
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "field_errors": {},
                },
            },
            status=exc.status_code,
        )

    if response is not None:
        message = _extract_message(response.data)
        response.data = {
            "success": False,
            "error": {
                "code": "REQUEST_ERROR",
                "message": message,
                "field_errors": response.data if isinstance(response.data, dict) else {},
            },
        }

    return response


def _extract_message(data):
    """
    DRF error payloads come in different shapes:
      - {"detail": "some message"}                → use it directly
      - {"field": ["error1", "error2"]}            → join into one readable line
      - "plain string"                             → use as-is
    This normalizes all of them into one clean, human-readable string.
    """
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        parts = []
        for field, errors in data.items():
            if isinstance(errors, list):
                errors = ", ".join(str(e) for e in errors)
            parts.append(f"{field}: {errors}")
        return " | ".join(parts) if parts else "Something went wrong."

    if isinstance(data, list):
        return " | ".join(str(e) for e in data)

    return str(data)