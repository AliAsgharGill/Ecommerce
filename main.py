from fastapi import FastAPI, Request, status, HTTPException
from tortoise.contrib.fastapi import register_tortoise
from models import *

# Authentication
from authentication import *
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm


# signals
from tortoise.signals import post_save
from typing import List, Optional, Type
from tortoise import BaseDBAsyncClient
from emails import *


from fastapi.responses import HTMLResponse
import jwt
from dotenv import dotenv_values
from fastapi.templating import Jinja2Templates


config_crdentials = dotenv_values(".env")


app = FastAPI()


oath2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.post("/token")
async def generate_token(request_form: OAuth2PasswordRequestForm = Depends()):
    token = await token_generator(request_form.username, request_form.password)
    return {"access_token": token, "token_type": "bearer"}
    # user = await User.get(email=request_form.username)
    # if not user:
    #     raise HTTPException(status_code=400, detail="Invalid credentials")
    # if not pwd_context.verify(request_form.password, user.password):
    #     raise HTTPException(status_code=400, detail="Incorrect password")
    # return {"access_token": user.id, "token_type": "bearer"}


async def get_current_user(token: str = Depends(oath2_scheme)):
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


@app.post("/user/me")
async def user_login(user: user_pydanticIn = Depends(get_current_user)):
    business = await Business.get(owner=user)
    return {
        "status": "ok",
        "data": {
            "username": user.username,
            "email": user.email,
            "verified": user.is_verified,
            "joined_date": user.join_date.strftime("%b-%m-%Y"),
        },
    }


@post_save(User)
async def user_post_save(
    sender: Type[User],
    instance: User,
    created: bool,
    using_db: "Optional[BaseDBAsyncClient]",
    update_fields: List[str],
) -> None:
    if created:
        business_obj = await Business.create(
            business_name=instance.username, owner=instance
        )
        await business_pydantic.from_tortoise_orm(business_obj)
        # send email to user #Note
        await send_email(EmailSchema(email=[instance.email]), instance)
    print(f"User {instance.username} has been created successfully.")


@app.post("/registration")
async def user_registration(user: user_pydanticIn):
    user_info = user.dict(exclude_unset=True)
    user_info["password"] = await get_hash_password(user_info["password"])

    # return await User.create(**user_info)
    user_obj = await User.create(**user_info)
    new_user = await user_pydantic.from_tortoise_orm(user_obj)
    return {
        "status": "ok",
        "data": f"Hello {new_user.username}, your account has been created successfully. Please verify your {new_user.email} email address to activate your account.",
    }


templates = Jinja2Templates(directory="templates")


@app.get("/verification", response_class=HTMLResponse)
async def email_verification(token: str, request: Request):
    try:
        user = await verify_token(token)
        if user and not user.is_verified:
            user.is_verified = True
            await user.save()
            return templates.TemplateResponse(
                "verification.html",
                {
                    "request": request,
                    "user": user.username,
                    "message": "Your email has been verified successfully.",
                },
            )
    except jwt.ExpiredSignatureError:
        return HTMLResponse(
            content="<h1>Verification link has expired.</h1>",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    except jwt.InvalidTokenError:
        return HTMLResponse(
            content="<h1>Invalid token.</h1>",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


@app.get("/")
async def root():
    return {"message": "Hello World"}


# Registering the Tortoise ORM models with FastAPI
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)
