from typing import Generic, TypeVar, Optional, Any, List
from pydantic import BaseModel

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Operation successful"
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str = "An error occurred"
    errors: List[Any] = []
