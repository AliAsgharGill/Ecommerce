from fastapi import (
    BackgroundTasks,
    UploadFile,
    File,
    Form,
    Depends,
    HTTPException,
    status,
)
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from dotenv import dotenv_values
from pydantic import BaseModel, EmailStr
from typing import List
from models import User
import jwt


config_crdentials = dotenv_values(".env")

conf = ConnectionConfig(
    MAIL_USERNAME=config_crdentials["EMAIL"],
    MAIL_PASSWORD=config_crdentials["PASSWORD"],
    MAIL_FROM=config_crdentials["EMAIL"],
    MAIL_PORT=587,  # Port for STARTTLS
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,  # Use STARTTLS
    MAIL_SSL_TLS=False,  # Disable SSL/TLS
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)


class EmailSchema(BaseModel):
    email: List[EmailStr]


async def send_email(email: EmailSchema, instance: User):
    token_data = {
        "id": instance.id,
        "email": instance.email,
        "username": instance.username,
        # Ensure all keys and values are valid
    }

    token = jwt.encode(token_data, config_crdentials["SECRET"], algorithm="HS256")

    template = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>Email Verification</title>
        </head>
        <body style="font-family: Arial, sans-serif; background-color: #f2f2f2; padding: 20px; text-align: center; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #fff; padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1); " >

            <h1>Hello {instance.username},</h1>
            <p>Please verify your email address by clicking the link below:</p>
            <a href="http://localhost:8000/verification/?token={token}" style="display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px;" >Verify Email</a>

            <p>Thank you for choosing our platform.</p>
            
            
            
            <p>If you are having trouble clicking the link, copy and paste the URL below into your web browser:</p>
            <a href="http://localhost:8000/verification/?token={token}">http://localhost:8000/verification/?token={token}</a>
            
            <p>For security purposes, please do not share this email address with anyone else.</p>
            <p>This email is confidential and intended for the sole use of the recipient.</p>
            <p>If you have any questions or concerns, please contact us at <a href="mailto:stylinalivlogs@gmail.com">stylinalivlogs@gmail.com</a></p>
            
            
            <p>Please kindly ignore this email if you did not register on our platform.</p>
            <p>This email is automatically generated. Please do not reply.</p>
            <p>&copy; 2024 All rights reserved.</p>

            <p>Best regards,</p>
            <p>"Ali Asghar Gill"</p>
            
        </div>
        </body>
    </html>
    """
    recipient_email = str(instance.email)
    message = MessageSchema(
        subject="E-commerce Email Verification",
        recipients=[recipient_email],
        body=template,
        subtype="html",
    )
    fm = FastMail(conf)
    await fm.send_message(message)
