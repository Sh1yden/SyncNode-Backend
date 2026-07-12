from fastapi import APIRouter, status

from app.schemas import DefaultSchema

router = APIRouter()


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Check API status",
    response_model=DefaultSchema,
)
@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Check API status",
    response_model=DefaultSchema,
)
def default_response():
    """Check API status"""
    return {"status": True}
