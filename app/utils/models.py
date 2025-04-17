from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product = Column(String, nullable=False)
    predicted_country = Column(String, nullable=False)
    manufacturing_date = Column(Date, nullable=False)
    predicted_shelf_life_days = Column(Integer, nullable=False)
    predicted_expiry_date = Column(Date, nullable=False)
    days_left = Column(Integer, nullable=False)


# Function to save prediction data to the database
def save_prediction(
    db: Session,
    product: str,
    predicted_country: str,
    manufacturing_date: str,
    predicted_shelf_life_days: int,
    predicted_expiry_date: str,
    days_left: int
):
    # Create a new product object
    new_product = Product(
        product=product,
        predicted_country=predicted_country,
        manufacturing_date=manufacturing_date,
        predicted_shelf_life_days=predicted_shelf_life_days,
        predicted_expiry_date=predicted_expiry_date,
        days_left=days_left
    )
    
    # Add the new product to the session
    db.add(new_product)
    
    # Commit the transaction
    db.commit()
    
    # Refresh to get the id of the new product
    db.refresh(new_product)

    return new_product 
