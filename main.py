from fastapi import FastAPI, Request, status, HTTPException
from tortoise.contrib.fastapi import register_tortoise
from models import *
from authentication import get_hash_password, verify_token

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
