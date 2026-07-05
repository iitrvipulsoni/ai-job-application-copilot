from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import uuid
import jwt
from datetime import datetime, timedelta, timezone
import bcrypt
from typing import Optional

from database import get_db
from models import User, AuditLog, AuditLogStatus
from schemas import Token, UserRegister, UserLogin
from config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")
    return encoded_jwt

def seed_default_user_if_needed(db: Session):
    """
    Seed dev@example.com with password123 if there are zero users in the database.
    """
    try:
        user_count = db.query(User).count()
        if user_count == 0:
            dev_user = User(
                id=uuid.uuid4(),
                email="dev@example.com",
                hashed_password=get_password_hash("password123")
            )
            db.add(dev_user)
            db.commit()
            db.refresh(dev_user)
            print("Seeded default user: dev@example.com / password123")
    except Exception as e:
        print(f"Error seeding user: {e}")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """
    Extract user from JWT access token. Seeds default user if db is empty.
    """
    seed_default_user_if_needed(db)
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        # Check if there is an Authorization header that starts with "Bearer " (case insensitive fallback)
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user (Candidate profile) for Private Beta.
    """
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    # Hash the password and save to database
    hashed_pwd = get_password_hash(payload.password)
    new_user = User(
        id=uuid.uuid4(),
        email=payload.email,
        hashed_password=hashed_pwd
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Add audit log
    audit_entry = AuditLog(
        user_id=new_user.id,
        action="user_registered",
        status=AuditLogStatus.SUCCESS,
        details={"email": new_user.email}
    )
    db.add(audit_entry)
    db.commit()

    return {"message": "User registered successfully.", "email": new_user.email}

async def get_login_form(request: Request) -> Optional[OAuth2PasswordRequestForm]:
    try:
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")
            if username and password:
                class MockForm:
                    def __init__(self, username, password):
                        self.username = username
                        self.password = password
                return MockForm(username, password)
    except Exception:
        pass
    return None

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    json_data: Optional[UserLogin] = None,
    db: Session = Depends(get_db)
):
    """
    OAuth2 Password Bearer compatible login. Handles both JSON body and standard Form body login.
    """
    # 1. Resolve email and password from input sources
    email = None
    password = None

    if json_data:
        email = json_data.email
        password = json_data.password
    else:
        form_data = await get_login_form(request)
        if form_data:
            email = form_data.username
            password = form_data.password

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request. Email and password are required."
        )

    # Make sure default user is seeded in case login is called first
    seed_default_user_if_needed(db)

    # 2. Fetch user and verify credentials
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Create access token
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return {"access_token": access_token, "token_type": "bearer"}
