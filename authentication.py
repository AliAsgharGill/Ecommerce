from passlib.context import CryptContext
import jwt
from dotenv import dotenv_values
from models import User
from fastapi import HTTPException

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
from dotenv import dotenv_values


config_crdentials = dotenv_values(".env")


async def get_hash_password(password: str):
    """
    Hashes a password using bcrypt.

    Args:
        password (str): The password to hash.

    Returns:
        str: The hashed password.
    """
    return pwd_context.hash(password)


async def verify_token(token: str):
    try:
        payload = jwt.decode(token, config_crdentials["SECRET"], algorithms=["HS256"])
        user_id = payload["id"]
        user = await User.get(id=user_id)
        await user.save()
        return user
    except jwt.exceptions.InvalidTokenError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
