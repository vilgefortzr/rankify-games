from django.db import IntegrityError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    MethodNotAllowed,
    ParseError,
    NotFound,
    UnsupportedMediaType,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler


def error_response(code, message, details=None):
    body = {"status": code, "message": message}
    if details is not None:
        body["details"] = details
    return Response({"error": body}, status=code)


def custom_exception_handler(exc, context):
    if isinstance(exc, IntegrityError):
        return error_response(status.HTTP_409_CONFLICT, "Конфлікт даних: такий запис уже існує.")

    response = exception_handler(exc, context)
    if response is None:
        return error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "Внутрішня помилка сервера.")

    code = response.status_code
    if isinstance(exc, ValidationError):
        return error_response(code, "Некоректні дані.", response.data)
    if isinstance(exc, ParseError):
        return error_response(code, "Некоректний JSON у тілі запиту.")
    if isinstance(exc, UnsupportedMediaType):
        return error_response(code, "Підтримується лише Content-Type: application/json.")
    if isinstance(exc, MethodNotAllowed):
        return error_response(code, f"Метод {context['request'].method} не підтримується для цієї адреси.")
    if isinstance(exc, (Http404, NotFound)):
        message = str(exc.detail) if hasattr(exc, "detail") and exc.detail else "Об'єкт не знайдено."
        return error_response(code, message)
    return error_response(code, response.data.get("detail", "Помилка запиту."))
