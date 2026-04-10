from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.core.time_utils import UTC
from fastapi import HTTPException, status
import os


# =====================================================
# CONFIG
# =====================================================

SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =====================================================
# PASSWORD HANDLING
# =====================================================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# =====================================================
# JWT CREATION
# =====================================================

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# =====================================================
# JWT DECODING (STRICT VERSION)
# =====================================================

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
