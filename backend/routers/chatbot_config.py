from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models, schemas
from database import get_db
from dependencies import get_current_user

router = APIRouter(prefix="/api/chatbot-config", tags=["chatbot_config"])

@router.get("", response_model=schemas.ChatbotConfigResponse)
def get_chatbot_config(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    config = db.query(models.ChatbotConfig).filter(models.ChatbotConfig.tenant_id == current_user.tenant_id).first()
    
    if not config:
        # Create default config if it doesn't exist
        config = models.ChatbotConfig(tenant_id=current_user.tenant_id)
        db.add(config)
        db.commit()
        db.refresh(config)
        
    return config

@router.put("", response_model=schemas.ChatbotConfigResponse)
def update_chatbot_config(
    config_update: schemas.ChatbotConfigCreate,
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=404, detail="User has no associated tenant")
        
    config = db.query(models.ChatbotConfig).filter(models.ChatbotConfig.tenant_id == current_user.tenant_id).first()
    
    if not config:
        config = models.ChatbotConfig(tenant_id=current_user.tenant_id)
        db.add(config)
        
    config.theme_color = config_update.theme_color
    config.widget_title = config_update.widget_title
    config.greeting_message = config_update.greeting_message
    config.position = config_update.position
    config.welcome_delay = config_update.welcome_delay
    config.max_history = config_update.max_history
    config.sound_enabled = config_update.sound_enabled
    
    db.commit()
    db.refresh(config)
    return config
