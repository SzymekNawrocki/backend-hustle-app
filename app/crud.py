from sqlalchemy.orm import Session
from . import models, schemas

def get_items(db: Session):
    return db.query(models.HustleItem).all()

def create_item(db: Session, item: schemas.HustleItemCreate):
    db_item = models.HustleItem(
        title=item.title, 
        category=item.category, 
        value=item.value
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item