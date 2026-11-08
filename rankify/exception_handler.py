from rest_framework import status
from rest_framework.exceptions import APIException, ErrorDetail
from rest_framework.views import exception_handler


class ConflictError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The request conflicts with the current state of the resource."
    default_code = "conflict"


class SteamUnavailableError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Steam API is temporarily unavailable. Please try again later."
    default_code = "steam_unavailable"


def error_body(status_code, code, message, details=None):
    return {
        "error": {
            "status": status_code,
            "code": code,
            "message": message,
            "details": details,
        }
    }


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    detail = data.get("detail") if isinstance(data, dict) else None
    if isinstance(detail, ErrorDetail):
        response.data = error_body(response.status_code, detail.code, str(detail))
    else:
        response.data = error_body(
            response.status_code, exc.default_code, str(exc.default_detail), data
        )
    return response
