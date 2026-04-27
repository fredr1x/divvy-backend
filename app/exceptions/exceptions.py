import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.exceptions")


class DivvyError(Exception):
    def __init__(self, message: str, error_code: str, resolution: str, status_code: int):
        self.message = message
        self.error_code = error_code
        self.resolution = resolution
        self.status_code = status_code
        super().__init__(message)


class AccountNotVerified(DivvyError):
    def __init__(self):
        super().__init__(
            message="Account Not Verified",
            error_code="account_not_verified",
            resolution="Please check your email for verification details",
            status_code=status.HTTP_403_FORBIDDEN,
        )


def create_exception_handler(status_code: int, initial_detail: dict[str, Any]):
    async def exception_handler(_: Request, __: Exception):
        return JSONResponse(
            status_code=status_code,
            content={"error": initial_detail},
        )

    return exception_handler


async def divvy_error_handler(_: Request, exc: DivvyError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "error_code": exc.error_code,
                "resolution": exc.resolution,
            }
        },
    )


async def validation_error_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "message": "Request validation failed",
                "error_code": "validation_error",
                "resolution": "Check request fields and types",
                "details": exc.errors(),
            }
        },
    )


async def unhandled_error_handler(_: Request, exc: Exception):
    logger.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "message": "Something went wrong",
                "error_code": "internal_error",
                "resolution": "Please try again later",
            }
        },
    )


def register_all_errors(app: FastAPI):
    app.add_exception_handler(
        AccountNotVerified,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "Account Not Verified",
                "error_code": "account_not_verified",
                "resolution": "Please check your email for verification details",
            },
        ),
    )
    app.add_exception_handler(DivvyError, divvy_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
