from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models, schemas
from database import get_db
from dependencies import get_current_user

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
    current_user: models.User = Depends(get_current_user), 
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

from typing import List
import uuid
from datetime import datetime, timedelta

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
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
    
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == invite.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=7)

    new_invite = models.TenantInvite(
        email=invite.email,
        token=token,
        tenant_id=current_user.tenant_id,
        role=invite.role,
        database_ids=",".join(map(str, invite.database_ids)) if invite.database_ids else None,
        expires_at=expires_at
    )
    db.add(new_invite)
    db.commit()

    import os
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    invite_link = f"{frontend_url}/signup?invite_token={token}"
    return {"invite_link": invite_link, "email": invite.email}

@router.delete("/members/{user_id}")
def remove_tenant_member(
    user_id: int,
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Only Admins can remove members")
        
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself")
        
    member_to_remove = db.query(models.User).filter(
        models.User.id == user_id, 
        models.User.tenant_id == current_user.tenant_id
    ).first()
    
    if not member_to_remove:
        raise HTTPException(status_code=404, detail="Member not found in this organization")
        
    db.delete(member_to_remove)
    db.commit()
    
    return {"message": "Member removed successfully"}
