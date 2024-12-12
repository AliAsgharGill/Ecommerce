from tortoise import Model, fields
from tortoise.contrib.pydantic import pydantic_model_creator
from datetime import datetime


class User(Model):
    id = fields.IntField(pk=True, index=True)
    username = fields.CharField(max_length=50, null=False, unique=True)
    email = fields.CharField(max_length=50, null=False, unique=True)
    password = fields.CharField(max_length=80, null=False)
    is_verified = fields.BooleanField(default=False)
    join_date = fields.DatetimeField(auto_now_add=True, default=datetime.now)


class Business(Model):
    id = fields.IntField(pk=True, index=True)
    business_name = fields.CharField(max_length=100, null=False, unique=True)
    city = fields.CharField(max_length=50, null=False, default="Unspecified")
    region = fields.CharField(max_length=50, null=False, default="Unspecified")
    business_description = fields.TextField(null=True)
    logo = fields.CharField(max_length=100, null=True, default="default.jpg")
    owner = fields.ForeignKeyField("models.User", related_name="businesses")


class Product(Model):
    id = fields.IntField(pk=True, index=True)
    name = fields.CharField(max_length=100, null=False, unique=True)
    category = fields.CharField(max_length=50, index=True)
    original_price = fields.DecimalField(max_digits=10, decimal_places=2)
    new_price = fields.DecimalField(max_digits=10, decimal_places=2)
    percentage_discount = fields.IntField()
    offer_expiriation_date = fields.DateField(default=datetime.now)
    product_description = fields.TextField(null=True)
    product_image = fields.CharField(
        max_length=100, null=True, default="productDefault.jpg"
    )
    date_published = fields.DatetimeField(auto_now_add=True, default=datetime.now, null=True) # null means that the field is not required
    business = fields.ForeignKeyField("models.Business", related_name="products")


user_pydantic = pydantic_model_creator(User, name="User", exclude=("is_verified",))
user_pydanticIn = pydantic_model_creator(
    User, name="UserIn", exclude_readonly=True, exclude=("is_verified",)
)
user_pydanticOut = pydantic_model_creator(
    User,
    name="UserOut",
    exclude=(
        "password",
        "is_verified",
    ),
)

business_pydantic = pydantic_model_creator(Business, name="Business")
business_pydanticIn = pydantic_model_creator(
    Business, name="BusinessIn", exclude_readonly=True, exclude=("logo", "id")
)


product_pydantic = pydantic_model_creator(
    Product, name="Product", exclude=("business",)
)
product_pydanticIn = pydantic_model_creator(
    Product,
    name="ProductIn",
    exclude_readonly=True,
    exclude=("percentage_discount", "id", "date_published", "product_image"),
)
product_pydanticOut = pydantic_model_creator(
    Product, name="ProductOut", exclude=("business",)
)
