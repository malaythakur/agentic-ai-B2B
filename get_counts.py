"""Get exact database counts"""
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.models import ServiceProvider, BuyerCompany, Match
import os
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/outbound")
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
db = Session()

buyers = db.query(BuyerCompany).count()
providers = db.query(ServiceProvider).count()
matches = db.query(Match).count()

print(f"\n{'='*60}")
print(f"DATABASE COUNTS")
print(f"{'='*60}")
print(f"Buyers:     {buyers}")
print(f"Providers:  {providers}")
print(f"Matches:    {matches}")
print(f"{'='*60}\n")

# Count by industry
print("Buyers by Industry:")
industries = ["technology", "healthcare", "finance", "manufacturing", "retail", 
              "construction", "education", "energy", "transportation", "media",
              "agriculture", "real_estate", "legal", "hospitality", "nonprofit"]

for ind in industries:
    count = db.query(BuyerCompany).filter(BuyerCompany.industry == ind).count()
    print(f"  {ind:20s}: {count}")

db.close()
