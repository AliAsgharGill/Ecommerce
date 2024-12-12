from fastapi import FastAPI, Request, status, HTTPException
from tortoise.contrib.fastapi import register_tortoise
from tortoise.contrib.pydantic import pydantic_queryset_creator
from models import *

# Authentication
from authentication import *
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm


# signals
from tortoise.signals import post_save
from typing import List, Optional, Type
from tortoise import BaseDBAsyncClient


from emails import *

# response class
from fastapi.responses import HTMLResponse

import jwt
from dotenv import dotenv_values

# templates
from fastapi.templating import Jinja2Templates


# image upload
from fastapi import UploadFile, File
from fastapi.staticfiles import StaticFiles
from PIL import Image
from io import BytesIO
from typing import Optional
import secrets

config_credentials = dotenv_values(".env")


app = FastAPI()


oath2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# static file setup config
app.mount("/static", StaticFiles(directory="static"), name="static")


# token generator configuration
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


# current user details
async def get_current_user(token: str = Depends(oath2_scheme)):
    try:
        payload = jwt.decode(token, config_credentials["SECRET"], algorithms=["HS256"])
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


# user details
@app.post("/user/me")
async def user_login(user: user_pydanticIn = Depends(get_current_user)):
    business = await Business.get(owner=user)
    logo = business.logo
    logo_path = f"localhost:8000/static/images/profile_images/{logo}"
    return {
        "status": "ok",
        "data": {
            "username": user.username,
            "email": user.email,
            "verified": user.is_verified,
            "joined_date": user.join_date.strftime("%b-%m-%Y"),
            "logo": logo_path,
        },
    }


# user signals
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
    print(f"User {instance.username} called successfully.")


# user registration
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


# email verification
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


# business image upload
@app.post("/uploadfile/profile")
async def create_upload_file(
    file: UploadFile = File(...), user: user_pydantic = Depends(get_current_user)
):
    FILEPATH = "./static/images/profile_images"
    filename = file.filename
    extension = filename.split(".")[-1]

    if extension not in ["jpg", "jpeg", "png", "webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are allowed.",
        )
    token_name = secrets.token_hex(10) + "." + extension
    path = f"{FILEPATH}/{token_name}"
    file_content = await file.read()

    with open(path, "wb") as f:
        f.write(file_content)

    # Pillow resize image
    image = Image.open(path)
    image = image.resize((400, 400))
    image.save(path)

    f.close()

    business = await Business.get(owner=user)
    owner = await business.owner

    image_url = "localhost:8000/static/images/profile_images/" + token_name

    if owner.id == user.id:
        business.logo = token_name
        await business.save()
        return {"status": "ok", "data": f"{image_url}"}

    raise HTTPException(404, detail="You are not the owner of this business.")


# product image upload
@app.post("/uploadfile/product/{product_id}")
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    user: user_pydantic = Depends(get_current_user),
):
    FILEPATH = "./static/images/product_images"
    filename = file.filename
    extension = filename.split(".")[-1]

    if extension not in ["jpg", "jpeg", "png", "webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are allowed.",
        )
    token_name = secrets.token_hex(10) + "." + extension
    path = f"{FILEPATH}/{token_name}"
    file_content = await file.read()

    with open(path, "wb") as f:
        f.write(file_content)

    # resize image
    image = Image.open(path)
    image = image.resize((400, 400))
    image.save(path)

    f.close()

    product = await Product.get(id=product_id)
    business = await product.business
    owner = await business.owner

    if owner == user:
        product.product_image = token_name
        await product.save()
        return {
            "status": "ok",
            "data": f"localhost:8000/static/images/product_images/{token_name}",
        }
    raise HTTPException(404, detail="You are not the owner of this product.")


# business update request
@app.put("/business/{business_id}")
async def update_business(
    business_id: int,
    updated_business_info: business_pydanticIn,
    user: user_pydantic = Depends(get_current_user),
):
    business = await Business.get(id=business_id)
    owner = await business.owner

    if owner == user:
        updated_business_info = updated_business_info.dict(exclude_unset=True)
        business = await business.update_from_dict(updated_business_info)
        await business.save()
        response = await business_pydantic.from_tortoise_orm(business)
        return {"status": "ok", "data": response}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated to perform this action.",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Product CRUD methods
@app.post("/products")
async def create_new_product(
    product: product_pydanticIn, user: user_pydantic = Depends(get_current_user)
):
    product_info = product.dict(exclude_unset=True)
    # to avoid division by zero
    if product_info["original_price"] > 0:
        product_info["percentage_discount"] = (
            (product_info["original_price"] - product_info["new_price"])
            / product_info["original_price"]
            * 100
        )
        product_obj = await Product.create(
            **product_info, business=user
        )  # product created and linked to the business and saved in the database
        new_product = await product_pydantic.from_tortoise_orm(
            product_obj
        )  # product to be sent to frontend
        return {"status": "ok", "data": new_product}
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Original price must be greater than 0.",
    )


@app.get("/product")
async def get_all_products():
    response = await product_pydantic.from_queryset(Product.all())
    return {"status": "ok", "data": response}


@app.get("/product/{product_id}")
async def get_product_by_id(product_id: int):
    product = await Product.get(id=product_id)
    business = await product.business
    owner = await business.owner
    response = await product_pydantic.from_tortoise_orm(product)

    return {
        "status": "ok",
        "data": {
            "product_details": response,
            "business_details": {
                "name": business.business_name,
                "city": business.city,
                "region": business.region,
                "business_description": business.business_description,
                "logo": f"localhost:8000/static/images/profile_images/{business.logo}",
                "owner_id": owner.id,
                "email": owner.email,
                "joined_date": owner.join_date.strftime("%b-%m-%Y"),
            },
        },
    }


@app.put("/product/{product_id}")
async def update_product(
    product_id: int,
    updated_product_info: product_pydanticIn,
    user: user_pydantic = Depends(get_current_user),
):
    product = await Product.get(id=product_id)
    business = await product.business
    owner = await business.owner

    updated_product_info = updated_product_info.dict(exclude_unset=True)
    updated_product_info["date_published"] = datetime.now()

    if user == owner and updated_product_info["original_price"] > 0:
        updated_product_info["original_price"] = updated_product_info["original_price"]
        updated_product_info["percentage_discount"] = (
            (updated_product_info["original_price"] - updated_product_info["new_price"])
            / updated_product_info["original_price"]
            * 100
        )
        product = await product.update_from_dict(updated_product_info)
        await product.save()
        response = await product_pydantic.from_tortoise_orm(product)
        return {"status": "ok", "data": response}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated to perform this action or original price must be greater than 0.",
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.delete("/product/{product_id}")
async def delete_product(
    product_id: int, user: user_pydantic = Depends(get_current_user)
):
    product = await Product.get(id=product_id)
    business = await product.business
    owner = await business.owner

    if owner == user:
        await product.delete()
        return {"status": "ok", "data": "Product deleted successfully."}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated to perform this action.",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Registering the Tortoise ORM models with FastAPI
register_tortoise(
    app,
    db_url="sqlite://db.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)
