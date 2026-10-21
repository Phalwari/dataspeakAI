from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import cast, Any
import models, schemas, auth
from database import get_db
from google.oauth2 import id_token
from google.auth.transport import requests
import random
import uuid
import os
import resend

router = APIRouter(prefix="/api/auth", tags=["auth"])

AVATARS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "avatars")
os.makedirs(AVATARS_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}



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
            if invite.expires_at < datetime.now(timezone.utc):
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

            # Initialize default TenantSettings (Stage 4A)
            tenant_settings = models.TenantSettings(
                tenant_id=tenant_id,
                theme_mode="light",
                notifications_enabled=True
            )
            db.add(tenant_settings)

        hashed_password = auth.get_password_hash(user.password)
        new_user = models.User(
            email=user_email,
            full_name=user.full_name,
            hashed_password=hashed_password,
            tenant_id=tenant_id,
            role=role,
            is_platform_admin=False
        )
        db.add(new_user)
        db.flush() # Populate new_user.id
        
        # Initialize Membership record (Stage 4A)
        matched_role = db.query(models.Role).filter(models.Role.name == role).first()
        membership = models.Membership(
            user_id=new_user.id,
            tenant_id=tenant_id,
            role_id=matched_role.id if matched_role else None,
            is_owner=(not bool(user.invite_token))
        )
        db.add(membership)
        
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
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        otp_entry = models.PasswordResetOTP(email=user_email, otp_code=otp_code, expires_at=expires_at)
        db.add(otp_entry)
        db.commit()
        
        send_otp_email(user_email, otp_code, "Verify your email", "Your verification code is")

        return {
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": new_user.role,
            "is_platform_admin": getattr(new_user, "is_platform_admin", False),
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
    
    if not getattr(db_user, "is_active", True):
        raise HTTPException(status_code=403, detail="User account is inactive or disabled")

    if not db_user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email before logging in.")
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": db_user.email, "tv": getattr(db_user, "token_version", 1)}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user": db_user}

import requests as sync_requests
import os

@router.post("/github-login", response_model=schemas.Token)
def github_login(data: schemas.GithubLoginRequest, db: Session = Depends(get_db)):
    try:
        client_id = os.getenv("GITHUB_CLIENT_ID")
        client_secret = os.getenv("GITHUB_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GitHub OAuth credentials (GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET) are not configured."
            )
        
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
                is_platform_admin=False,
                is_verified=True
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
        if not getattr(db_user, "is_active", True):
            raise HTTPException(status_code=403, detail="User account is inactive or disabled")

        access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth.create_access_token(
            data={"sub": db_user.email, "tv": getattr(db_user, "token_version", 1)}, expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer", "user": db_user}
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

from dependencies import get_current_user

@router.post("/change-password")
def change_password(data: schemas.UserChangePassword, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    current_hash = str(current_user.hashed_password or "")
    if not auth.verify_password(data.current_password, current_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    setattr(current_user, "hashed_password", auth.get_password_hash(data.new_password))
    # Bump token version to invalidate all other active sessions (Task NR-1.1-A-T05)
    current_user.token_version = getattr(current_user, "token_version", 1) + 1
    db.commit()
    return {"message": "Password updated successfully"}


@router.get("/me", response_model=schemas.UserResponse)
def get_user_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=schemas.UserResponse)
def update_user_me(
    profile_data: schemas.UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update profile information (full_name, email, phone, avatar_url)."""
    if profile_data.full_name is not None:
        name_clean = profile_data.full_name.strip()
        if not name_clean:
            raise HTTPException(status_code=400, detail="Name cannot be empty")
        current_user.full_name = name_clean

    if profile_data.email is not None:
        new_email = str(profile_data.email).lower().strip()
        if not new_email:
            raise HTTPException(status_code=400, detail="Email cannot be empty")
        if new_email != current_user.email:
            existing = db.query(models.User).filter(models.User.email == new_email).first()
            if existing and existing.id != current_user.id:
                raise HTTPException(status_code=400, detail="This email is already in use by another account")
            current_user.email = new_email

    if profile_data.phone is not None:
        current_user.phone = profile_data.phone.strip()

    if profile_data.avatar_url is not None:
        current_user.avatar_url = profile_data.avatar_url.strip() if profile_data.avatar_url else None

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/upload-avatar")
async def upload_user_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Upload and save user profile picture.
    Enforces strict 5MB limit and image format validation.
    """
    filename = file.filename or "avatar.png"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension '{ext}'. Only JPG, PNG, WEBP, and GIF images are supported."
        )

    # Check content type if provided
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image content type '{file.content_type}'."
        )

    # Read and validate size (Max 5MB = 5 * 1024 * 1024 bytes)
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds maximum limit of 5MB. Please upload an image under 5MB."
        )
    if len(contents) == 0:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    # Clean previous uploaded custom avatar file if present
    if current_user.avatar_url and current_user.avatar_url.startswith("/api/auth/avatar/"):
        old_filename = current_user.avatar_url.replace("/api/auth/avatar/", "").strip()
        if old_filename and ".." not in old_filename and "/" not in old_filename and "\\" not in old_filename:
            old_path = os.path.join(AVATARS_DIR, old_filename)
            if os.path.isfile(old_path):
                try:
                    os.remove(old_path)
                except Exception as ex:
                    print(f"[AVATAR] Old avatar cleanup note: {ex}")

    unique_filename = f"avatar_u{current_user.id}_{uuid.uuid4().hex[:10]}{ext}"
    file_path = os.path.join(AVATARS_DIR, unique_filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    avatar_url = f"/api/auth/avatar/{unique_filename}"
    current_user.avatar_url = avatar_url
    db.commit()
    db.refresh(current_user)

    return {
        "message": "Avatar uploaded successfully",
        "avatar_url": avatar_url,
        "user": current_user
    }


@router.delete("/avatar")
def remove_user_avatar(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Remove user custom profile picture and reset to initials."""
    if current_user.avatar_url and current_user.avatar_url.startswith("/api/auth/avatar/"):
        old_filename = current_user.avatar_url.replace("/api/auth/avatar/", "").strip()
        if old_filename and ".." not in old_filename:
            old_path = os.path.join(AVATARS_DIR, old_filename)
            if os.path.isfile(old_path):
                try:
                    os.remove(old_path)
                except Exception:
                    pass

    current_user.avatar_url = None
    db.commit()
    db.refresh(current_user)
    return {"message": "Avatar removed successfully", "avatar_url": None}


@router.get("/avatar/{filename}")
def get_avatar_image(filename: str):
    """Serve uploaded user avatar images."""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid avatar path")

    file_path = os.path.join(AVATARS_DIR, filename)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Avatar not found")

    ext = os.path.splitext(filename)[1].lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif"
    }
    media_type = media_types.get(ext, "application/octet-stream")
    return FileResponse(file_path, media_type=media_type, headers={"Cache-Control": "public, max-age=86400"})




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
            resend_payload: Any = {
                "from": "DataSpeakAI <onboarding@resend.dev>",
                "to": email,
                "subject": subject,
                "html": f"<p>{message}: <strong>{otp_code}</strong>. It expires in 10 minutes.</p>"
            }
            resend.Emails.send(resend_payload)
            print(f"SUCCESS: Email sent to {email} via Resend", flush=True)
        except Exception as e:
            print(f"ERROR: Resend Failed: {str(e)}", flush=True)
    else:
        if os.getenv("ENVIRONMENT", "development").lower() != "production":
            print(f"DEV NOTE: No email provider configured! Development OTP for {email} is: {otp_code}", flush=True)
        else:
            print(f"CRITICAL: No email provider configured! Failed to deliver OTP to {email}", flush=True)


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
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
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
        models.PasswordResetOTP.expires_at > datetime.now(timezone.utc)
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
        models.PasswordResetOTP.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if not otp_entry:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP session")
    
    db_user = db.query(models.User).filter(models.User.email == data.email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.hashed_password = auth.get_password_hash(data.new_password)
    # Bump token version to invalidate all active sessions upon password reset (Task NR-1.1-A-T05)
    db_user.token_version = getattr(db_user, "token_version", 1) + 1
    
    # Clean up OTP after use
    db.delete(otp_entry)
    db.commit()
    
    return {"message": "Password reset successfully"}

@router.post("/verify-email")
def verify_email(data: schemas.EmailVerificationRequest, db: Session = Depends(get_db)):
    otp_entry = db.query(models.PasswordResetOTP).filter(
        models.PasswordResetOTP.email == data.email,
        models.PasswordResetOTP.otp_code == data.otp_code,
        models.PasswordResetOTP.expires_at > datetime.now(timezone.utc)
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
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    # Clean up old OTPs for this email if any
    db.query(models.PasswordResetOTP).filter(models.PasswordResetOTP.email == data.email).delete()
    
    otp_entry = models.PasswordResetOTP(email=data.email, otp_code=otp_code, expires_at=expires_at)
    db.add(otp_entry)
    db.commit()
    
    send_otp_email(data.email, otp_code, "Verify your email", "Your verification code is")
    
    return {"message": "Verification code resent"}
