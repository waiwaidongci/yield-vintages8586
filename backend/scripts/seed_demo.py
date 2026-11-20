import json,random,hashlib,time
from src.config.database import Base,engine,Session
from src.config.settings import CONFIG
from src.models.identity import User
from src.models.source import Source,Policy,Period
from src.models import run
from src.utils.security import password_hash
from src.services.validation import validate_source
from src.services.calculation import calculate

def demo_rows():
 rng=random.Random(42);rows=[]
 for i in range(240):
  n=rng.randint(100,1200);fp=int(n*rng.uniform(.7,.96));rw=rng.randint(0,n-fp);rows.append({'period':'2026-11-'+str(1+i%20).zfill(2),'department':['试制线A','试制线B','试制线C'][i%3],'shift':['早班','晚班'][i%2],'input':n,'first_pass':fp,'reworked_good':rw,'scrap':n-fp-rw})
 return rows

# 核账演示：12个带批号批次（批号,日期,试制线,班次,投入,一次通过,返工合格,报废）
BATCH_ROWS=[
 ('P2026-001','2026-10-06','试制线A','早班',800,690,60,50),
 ('P2026-002','2026-10-07','试制线B','晚班',620,540,40,40),
 ('P2026-003','2026-10-13','试制线A','晚班',750,655,45,50),
 ('P2026-004','2026-10-14','试制线C','早班',900,800,60,40),
 ('P2026-005','2026-10-20','试制线B','早班',560,470,50,40),
 ('P2026-006','2026-10-21','试制线A','晚班',830,720,60,50),
 ('P2026-007','2026-11-03','试制线C','晚班',700,610,50,40),
 ('P2026-008','2026-11-04','试制线A','早班',880,770,70,40),
 ('P2026-009','2026-11-10','试制线B','早班',640,560,40,40),
 ('P2026-010','2026-11-11','试制线C','晚班',910,810,50,50),
 ('P2026-011','2026-11-17','试制线A','晚班',780,680,60,40),
 ('P2026-012','2026-11-18','试制线B','早班',850,740,60,50),
]
def batch_source(row,alter=None):
 b,period,dept,shift,inp,fp,rw,sc=row
 d={'period':period,'department':dept,'shift':shift,'input':inp,'first_pass':fp,'reworked_good':rw,'scrap':sc,'batch':b}
 if alter:d.update(alter)
 return d
def seed_recon(db):
 for i,row in enumerate(BATCH_ROWS):
  data=batch_source(row);validate_source(data);key='demo-batch-'+str(i+1)
  if not db.query(Source).filter_by(natural_key=key).first():db.add(Source(natural_key=key,data=data))
 policy=db.query(Policy).filter_by(version=CONFIG['policy']['version']).first()
 def mkrun(name,rows,review):
  if db.query(run.Run).filter_by(name=name).first():return
  snapshot={'policy':policy.data,'sources':rows,'period':'全部'}
  checksum=hashlib.sha256(json.dumps(snapshot,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
  obj=run.Run(name=name,status='completed',snapshot=snapshot,checksum=checksum,created=time.time(),approved=True,review=review)
  obj.result=calculate(rows,policy.data);db.add(obj)
 src={r[0]:batch_source(r) for r in BATCH_ROWS}
 mkrun('十月月报',[src[b]for b in('P2026-001','P2026-002','P2026-003','P2026-004','P2026-005','P2026-006')],'seed演示：月报已复核')
 mkrun('十一月月报',[src[b]for b in('P2026-007','P2026-008','P2026-009','P2026-010','P2026-011','P2026-012')],'seed演示：月报已复核')
 mkrun('专项-试制线A抽查',[src[b]for b in('P2026-003','P2026-004','P2026-008','P2026-011')],'seed演示：专项已复核')
 altered=batch_source(BATCH_ROWS[5],alter={'input':840,'first_pass':725,'reworked_good':60,'scrap':55})
 mkrun('专项-晚班复查',[src['P2026-005'],altered,src['P2026-011'],src['P2026-012']],'seed演示：专项已复核（P2026-006底数与月报不一致）')
 mkrun('旧口径季度汇总',demo_rows()[:6],'seed演示：无批号旧报告，可查但不参选')

def seed():
 Base.metadata.create_all(engine)
 with Session() as db:
  for role in ('admin','analyst','viewer'):
   if not db.query(User).filter_by(email=role+'@demo.local').first():db.add(User(email=role+'@demo.local',role=role,password=password_hash('Demo2026!')))
  rows=demo_rows()
  for name in sorted(set(r['period'] for r in rows)):
   if not db.query(Period).filter_by(name=name).first():db.add(Period(name=name,description='合成演示业务期间，seed=42'))
  for i,data in enumerate(rows):
   validate_source(data);key='demo-'+str(i+1)
   if not db.query(Source).filter_by(natural_key=key).first():db.add(Source(natural_key=key,data=data))
  if not db.query(Policy).filter_by(version=CONFIG['policy']['version']).first():db.add(Policy(version=CONFIG['policy']['version'],data=CONFIG['policy']))
  seed_recon(db)
  db.commit();print(json.dumps({'users':db.query(User).count(),'sources':db.query(Source).count(),'policies':db.query(Policy).count(),'periods':db.query(Period).count(),'runs':db.query(run.Run).count()},ensure_ascii=False))
if __name__=='__main__':seed()
