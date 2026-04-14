from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


_STATUS_CODES = {
    400: "VALIDATION_ERROR",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    413: "FILE_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "UNPROCESSABLE",
    500: "INTERNAL_SERVER_ERROR",
}


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return response

    code = _STATUS_CODES.get(response.status_code, "ERROR")
    field_errors = {}
    message = str(exc)

    # DRF validation errors have a dict / list structure
    if isinstance(response.data, dict):
        # "detail" is used by DRF for non-validation errors (404, 401, etc.)
        detail = response.data.pop("detail", None)
        if detail:
            message = str(detail)
        non_field = response.data.pop("non_field_errors", None)
        if non_field:
            message = " ".join(str(e) for e in non_field)
        # Remaining keys are field-level validation errors
        field_errors = {
            k: [str(e) for e in v] if isinstance(v, list) else [str(v)]
            for k, v in response.data.items()
        }
        if field_errors and code == "VALIDATION_ERROR":
            message = "Invalid request data."
    elif isinstance(response.data, list):
        message = " ".join(str(e) for e in response.data)

    response.data = {
        "error": {
            "code": code,
            "message": message,
            "field_errors": field_errors,
        }
    }
    return response
