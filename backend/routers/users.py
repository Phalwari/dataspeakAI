from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models, schemas, auth
from database import get_db
from google.oauth2 import id_token
from google.auth.transport import requests
import random
import uuid
import os
import resend

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    user_email = user.email.lower()
    db_user = db.query(models.User).filter(models.User.email == user_email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    tenant_id = None
    role = "Admin"

    try:
        if user.invite_token:
            invite = db.query(models.TenantInvite).filter(models.TenantInvite.token == user.invite_token).first()
            if not invite or invite.is_accepted:
                raise HTTPException(status_code=400, detail="Invalid or expired invite token")
            
            # Security Check: Ensure email matches the invitation
            if invite.email.lower() != user.email.lower():
                raise HTTPException(status_code=400, detail="This invite was sent to a different email address")
            
            # Security Check: Ensure invite hasn't expired
            if invite.expires_at < datetime.utcnow():
                raise HTTPException(status_code=400, detail="This invitation has expired")

            tenant_id = invite.tenant_id
            role = invite.role
            invite.is_accepted = True
        else:
            if not user.company_name:
                raise HTTPException(status_code=400, detail="Company name is required")
            new_tenant = models.Tenant(name=user.company_name)
            db.add(new_tenant)
            db.flush()
            tenant_id = new_tenant.id

        hashed_password = auth.get_password_hash(user.password)
        new_user = models.User(
            email=user_email,
            full_name=user.full_name,
            hashed_password=hashed_password,
            tenant_id=tenant_id,
            role=role
        )
        db.add(new_user)
        db.flush() # Populate new_user.id
        
        # Populate database access if this was an invite
        if user.invite_token:
            invite = db.query(models.TenantInvite).filter(models.TenantInvite.token == user.invite_token).first()
            if invite and invite.database_ids:
                db_ids = [int(id_str) for id_str in invite.database_ids.split(",") if id_str]
                for db_id in db_ids:
                    access = models.UserDatabaseAccess(user_id=new_user.id, database_id=db_id)
                    db.add(access)

        db.commit()
        
        # After commit, new_user.id is populated. 
        
        # Generate and send verification OTP
        otp_code = str(random.randint(100000, 999999))
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        otp_entry = models.PasswordResetOTP(email=user_email, otp_code=otp_code, expires_at=expires_at)
        db.add(otp_entry)
        db.commit()
        
        send_otp_email(user_email, otp_code, "Verify your email", "Your verification code is")

        return {
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": new_user.role,
            "is_active": new_user.is_active,
            "is_verified": new_user.is_verified,
            "tenant_id": new_user.tenant_id
        }

    except Exception as e:
        db.rollback()
        print(f"Registration error: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/login", response_model=schemas.Token)
def login_user(user: schemas.UserLogin, db: Session = Depends(get_db)):
    user_email = user.email.lower()
    db_user = db.query(models.User).filter(models.User.email == user_email).first()
    if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not db_user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email before logging in.")
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": db_user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user": db_user}

import requests as sync_requests
import os

@router.post("/github-login", response_model=schemas.Token)
def github_login(data: schemas.GithubLoginRequest, db: Session = Depends(get_db)):
    try:
        # Exchange code for access token
        client_id = os.getenv("GITHUB_CLIENT_ID", "Ov23liPRgons4RlFv7FU")
        client_secret = os.getenv("GITHUB_CLIENT_SECRET", "067e59b3c050792898954f727be0dbdbfc5c590a")
        
        token_response = sync_requests.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": data.code
            },
            headers={"Accept": "application/json"}
        )
        token_json = token_response.json()
        
        if "error" in token_json:
            raise HTTPException(status_code=400, detail=token_json.get("error_description", "Invalid GitHub code"))
            
        access_token_github = token_json.get("access_token")
        
        # Get user info
        user_response = sync_requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token_github}"}
        )
        user_data = user_response.json()
        
        # GitHub might not return email if it's private, we need to fetch emails
        email = user_data.get("email")
        if not email:
            emails_response = sync_requests.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token_github}"}
            )
            emails = emails_response.json()
            primary_email = next((e["email"] for e in emails if e.get("primary")), None)
            email = primary_email or emails[0]["email"]
            
        name = user_data.get("name") or user_data.get("login")
        
        # Check if user exists
        db_user = db.query(models.User).filter(models.User.email == email).first()
        
        if not db_user:
            new_tenant = models.Tenant(name=f"{name}'s Company")
            db.add(new_tenant)
            db.flush()
            
            import secrets
            dummy_password = auth.get_password_hash(secrets.token_urlsafe(32))
            
            db_user = models.User(
                email=email,
                full_name=name,
                hashed_password=dummy_password,
                tenant_id=new_tenant.id,
                role="Admin",
                is_verified=True
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
        access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth.create_access_token(
            data={"sub": db_user.email}, expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer", "user": db_user}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

from dependencies import get_current_user

@router.post("/change-password")
def change_password(data: schemas.UserChangePassword, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if not auth.verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    current_user.hashed_password = auth.get_password_hash(data.new_password)
    db.commit()
    return {"message": "Password updated successfully"}

@router.get("/me", response_model=schemas.UserResponse)
def get_user_me(current_user: models.User = Depends(get_current_user)):
    return current_user



import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_otp_email(email: str, otp_code: str, subject: str, message: str):
    print(f"DEBUG: Starting send_otp_email for {email}", flush=True)
    # Try SMTP first (Gmail, etc.)
    smtp_user = os.getenv("EMAIL_USER")
    smtp_pass = os.getenv("EMAIL_PASS")
    smtp_host = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("EMAIL_PORT", 587))

    if smtp_user and smtp_pass:
        print(f"DEBUG: Attempting SMTP with user: {smtp_user}", flush=True)
        try:
            msg = MIMEMultipart()
            msg['From'] = f"DataSpeakAI <{smtp_user}>"
            msg['To'] = email
            msg['Subject'] = subject
            
            body = f"{message}: {otp_code}. It expires in 10 minutes."
            msg.attach(MIMEText(body, 'plain'))
            
            # HTML version
            html = f"<p>{message}: <strong>{otp_code}</strong>. It expires in 10 minutes.</p>"
            msg.attach(MIMEText(html, 'html'))

            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
            print(f"SUCCESS: Email sent to {email} via SMTP", flush=True)
            return
        except Exception as e:
            print(f"ERROR: SMTP Failed: {str(e)}", flush=True)

    # Fallback to Resend if SMTP fails or isn't configured
    api_key = os.getenv("RESEND_API_KEY")
    if api_key:
        print("DEBUG: Falling back to Resend API", flush=True)
        try:
            resend.api_key = api_key
            resend.Emails.send({
                "from": "DataSpeakAI <onboarding@resend.dev>",
                "to": email,
                "subject": subject,
                "html": f"<p>{message}: <strong>{otp_code}</strong>. It expires in 10 minutes.</p>"
            })
            print(f"SUCCESS: Email sent to {email} via Resend", flush=True)
        except Exception as e:
            print(f"ERROR: Resend Failed: {str(e)}", flush=True)
    else:
        print(f"CRITICAL: No email provider configured! OTP for {email} is: {otp_code}", flush=True)

@router.post("/forgot-password")
def forgot_password(data: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    user_email = data.email.lower()
    print(f"DEBUG: Forgot Password request received for '{user_email}'", flush=True)
    db_user = db.query(models.User).filter(models.User.email == user_email).first()
    if not db_user:
        print(f"DEBUG: User not found in database: '{user_email}'", flush=True)
        # We don't want to reveal if a user exists or not for security
        return {"message": "If an account exists with that email, an OTP has been sent."}
    
    # Generate 6-digit OTP
    otp_code = str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # Save OTP to database
    try:
        otp_entry = models.PasswordResetOTP(
            email=user_email,
            otp_code=otp_code,
            expires_at=expires_at
        )
        db.add(otp_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"ERROR: Database error saving OTP: {str(e)}", flush=True)
        raise HTTPException(status_code=500, detail="Database error generating OTP")
    
    # Send Email via Resend
    send_otp_email(user_email, otp_code, "Your Password Reset OTP", "Your OTP for password reset is")
    
    return {"message": "If an account exists with that email, an OTP has been sent."}

@router.post("/verify-otp")
def verify_otp(data: schemas.VerifyOTPRequest, db: Session = Depends(get_db)):
    otp_entry = db.query(models.PasswordResetOTP).filter(
        models.PasswordResetOTP.email == data.email,
        models.PasswordResetOTP.otp_code == data.otp_code,
        models.PasswordResetOTP.expires_at > datetime.utcnow()
    ).first()
    
    if not otp_entry:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    return {"message": "OTP verified successfully"}

@router.post("/reset-password")
def reset_password(data: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    # Re-verify OTP for security during reset
    otp_entry = db.query(models.PasswordResetOTP).filter(
        models.PasswordResetOTP.email == data.email,
        models.PasswordResetOTP.otp_code == data.otp_code,
        models.PasswordResetOTP.expires_at > datetime.utcnow()
    ).first()
    
    if not otp_entry:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP session")
    
    db_user = db.query(models.User).filter(models.User.email == data.email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.hashed_password = auth.get_password_hash(data.new_password)
    
    # Clean up OTP after use
    db.delete(otp_entry)
    db.commit()
    
    return {"message": "Password reset successfully"}

@router.post("/verify-email")
def verify_email(data: schemas.EmailVerificationRequest, db: Session = Depends(get_db)):
    otp_entry = db.query(models.PasswordResetOTP).filter(
        models.PasswordResetOTP.email == data.email,
        models.PasswordResetOTP.otp_code == data.otp_code,
        models.PasswordResetOTP.expires_at > datetime.utcnow()
    ).first()
    
    if not otp_entry:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
    
    db_user = db.query(models.User).filter(models.User.email == data.email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.is_verified = True
    db.delete(otp_entry)
    db.commit()
    
    return {"message": "Email verified successfully"}

@router.post("/resend-verification")
def resend_verification(data: schemas.ResendVerificationRequest, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == data.email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if db_user.is_verified:
        return {"message": "Email is already verified"}
    
    # Generate and send new verification OTP
    otp_code = str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # Clean up old OTPs for this email if any
    db.query(models.PasswordResetOTP).filter(models.PasswordResetOTP.email == data.email).delete()
    
    otp_entry = models.PasswordResetOTP(email=data.email, otp_code=otp_code, expires_at=expires_at)
    db.add(otp_entry)
    db.commit()
    
    send_otp_email(data.email, otp_code, "Verify your email", "Your verification code is")
    
    return {"message": "Verification code resent"}
