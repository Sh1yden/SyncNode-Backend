from fastapi import APIRouter, status

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=None,
    summary="Register a new user.",
)
async def register():
    pass


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=None,
    summary="Login a user.",
)
async def login():
    pass


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    response_model=None,
    summary="Refresh a user.",
)
async def refresh():
    pass


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    response_model=None,
    summary="Logout a user.",
)
async def logout():
    pass
