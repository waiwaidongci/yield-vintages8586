from sqlalchemy import Column,Integer,String,JSON,Text,Float
from src.config.database import Base
class Reconciliation(Base):
 __tablename__='reconciliations'
 id=Column(Integer,primary_key=True); name=Column(String(120)); request_key=Column(String(64),unique=True); status=Column(String(20))
 batches=Column(JSON); policy=Column(JSON); candidates=Column(JSON); excluded=Column(JSON)
 result=Column(JSON); error=Column(Text); checksum=Column(String(64))
 created=Column(Float); started=Column(Float); finished=Column(Float)
