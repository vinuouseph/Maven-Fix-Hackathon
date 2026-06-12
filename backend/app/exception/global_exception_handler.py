from fastapi import Request
from fastapi.responses import JSONResponse
from app.exception.spring_fix_exceptions import SpringFixException

async def spring_fix_exception_handler(request: Request, exc: SpringFixException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": exc.message,
            "status_code": exc.status_code
        }
    )