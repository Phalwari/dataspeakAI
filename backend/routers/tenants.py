import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db
from dependencies import get_current_user, require_tenant_admin
from services.email_service import send_email

router = APIRouter(prefix="/api/tenant", tags=["tenant"])


@router.get("/current", response_model=schemas.TenantResponse)
def get_current_tenant(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    tenant = db.query(models.Tenant).filter(models.Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    return tenant


@router.put("/current", response_model=schemas.TenantResponse)
def update_current_tenant(
    tenant_update: schemas.TenantUpdate,
    current_user: models.User = Depends(require_tenant_admin), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    tenant = db.query(models.Tenant).filter(models.Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    if tenant_update.website is not None:
        tenant.website = tenant_update.website
    if tenant_update.industry is not None:
        tenant.industry = tenant_update.industry
    if tenant_update.address is not None:
        tenant.address = tenant_update.address
        
    db.commit()
    db.refresh(tenant)
    return tenant


@router.get("/members", response_model=List[schemas.UserResponse])
def get_tenant_members(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    members = db.query(models.User).filter(models.User.tenant_id == current_user.tenant_id).all()
    return members


@router.post("/invite", response_model=schemas.InviteResponse)
def invite_member(
    invite: schemas.InviteCreate,
    current_user: models.User = Depends(require_tenant_admin), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
    
    # Check if active user already exists with this email
    existing_user = db.query(models.User).filter(models.User.email == invite.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    # Validate that all assigned database connection IDs strictly belong to current_user.tenant_id
    db_ids_str = None
    if invite.database_ids:
        tenant_db_ids = set(
            row[0] for row in db.query(models.DatabaseConnection.id).filter(
                models.DatabaseConnection.tenant_id == current_user.tenant_id
            ).all()
        )
        for db_id in invite.database_ids:
            if db_id not in tenant_db_ids:
                raise HTTPException(
                    status_code=404,
                    detail=f"Database connection {db_id} not found in this organization"
                )
        db_ids_str = ",".join(map(str, sorted(set(invite.database_ids))))

    token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    # Check for existing pending invite
    existing_invite = db.query(models.TenantInvite).filter(
        models.TenantInvite.email == invite.email,
        models.TenantInvite.tenant_id == current_user.tenant_id,
        models.TenantInvite.is_accepted == False
    ).first()

    if existing_invite:
        existing_invite.token = token
        existing_invite.role = invite.role
        existing_invite.database_ids = db_ids_str
        existing_invite.expires_at = expires_at
    else:
        new_invite = models.TenantInvite(
            email=invite.email,
            token=token,
            tenant_id=current_user.tenant_id,
            role=invite.role,
            database_ids=db_ids_str,
            expires_at=expires_at
        )
        db.add(new_invite)

    db.commit()

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    invite_link = f"{frontend_url}/signup?invite_token={token}"
    email_sent = send_email(
        to=invite.email,
        subject="You are invited to DataSpeakAI",
        text_body=(
            "You have been invited to join DataSpeakAI. "
            f"Open this link to create your account: {invite_link}"
        ),
        html_body=(
            "<p>You have been invited to join DataSpeakAI.</p>"
            f'<p><a href="{invite_link}">Create your account</a></p>'
        ),
    )
    return {"invite_link": invite_link, "email": invite.email, "email_sent": email_sent}


@router.patch("/members/{user_id}", response_model=schemas.UserResponse)
@router.put("/members/{user_id}", response_model=schemas.UserResponse)
def update_tenant_member(
    user_id: int,
    member_update: schemas.TenantMemberUpdate,
    current_user: models.User = Depends(require_tenant_admin),
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")

    member = db.query(models.User).filter(
        models.User.id == user_id,
        models.User.tenant_id == current_user.tenant_id
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found in this organization")

    # If updating role
    if member_update.role is not None:
        if member.role == "Admin" and member_update.role != "Admin":
            admin_count = db.query(models.User).filter(
                models.User.tenant_id == current_user.tenant_id,
                models.User.role == "Admin",
                models.User.is_active == True
            ).count()
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot demote the last remaining tenant administrator")
        
        member.role = member_update.role

        matched_role = db.query(models.Role).filter(models.Role.name == member_update.role).first()
        membership = db.query(models.Membership).filter(
            models.Membership.user_id == member.id,
            models.Membership.tenant_id == current_user.tenant_id
        ).first()
        if membership and matched_role:
            membership.role_id = matched_role.id

    # If updating active status (Task NR-1.1-A-T05)
    if member_update.is_active is not None:
        if member.role == "Admin" and member_update.is_active is False:
            admin_count = db.query(models.User).filter(
                models.User.tenant_id == current_user.tenant_id,
                models.User.role == "Admin",
                models.User.is_active == True
            ).count()
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot deactivate the last remaining tenant administrator")
        
        member.is_active = member_update.is_active
        if not member.is_active:
            # Revoke all active sessions immediately upon account deactivation
            member.token_version = getattr(member, "token_version", 1) + 1

    # If updating database_ids
    if member_update.database_ids is not None:
        if member_update.database_ids:
            tenant_db_ids = set(
                row[0] for row in db.query(models.DatabaseConnection.id).filter(
                    models.DatabaseConnection.tenant_id == current_user.tenant_id
                ).all()
            )
            for db_id in member_update.database_ids:
                if db_id not in tenant_db_ids:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Database connection {db_id} not found in this organization"
                    )

        db.query(models.UserDatabaseAccess).filter(
            models.UserDatabaseAccess.user_id == member.id
        ).delete()

        for db_id in set(member_update.database_ids):
            db.add(models.UserDatabaseAccess(user_id=member.id, database_id=db_id))

    db.commit()
    db.refresh(member)
    return member


@router.delete("/members/{user_id}")
def remove_tenant_member(
    user_id: int,
    current_user: models.User = Depends(require_tenant_admin), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself")
        
    member_to_remove = db.query(models.User).filter(
        models.User.id == user_id, 
        models.User.tenant_id == current_user.tenant_id
    ).first()
    
    if not member_to_remove:
        raise HTTPException(status_code=404, detail="Member not found in this organization")

    # Prevent deleting the last Admin
    if member_to_remove.role == "Admin":
        admin_count = db.query(models.User).filter(
            models.User.tenant_id == current_user.tenant_id,
            models.User.role == "Admin",
            models.User.is_active == True
        ).count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last remaining tenant administrator")
        
    db.query(models.UserDatabaseAccess).filter(models.UserDatabaseAccess.user_id == member_to_remove.id).delete()
    db.query(models.Membership).filter(models.Membership.user_id == member_to_remove.id).delete()
    db.delete(member_to_remove)
    db.commit()
    
    return {"message": "Member removed successfully"}
