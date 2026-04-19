from app.database import SessionLocal
from app.models import BuyerCompany

db = SessionLocal()
buyer = db.query(BuyerCompany).filter(BuyerCompany.buyer_id == 'real-optin-buyer-001').first()
if buyer:
    print(f'Buyer ID: {buyer.buyer_id}')
    print(f'Company: {buyer.company_name}')
    print(f'Email: {buyer.decision_maker_email}')
else:
    print('Buyer not found')
db.close()
