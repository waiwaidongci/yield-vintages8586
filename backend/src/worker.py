import time,json,traceback
from pathlib import Path
import redis
from src.config.database import Base,engine,Session
from src.config.settings import REDIS_URL
from src.models import identity,source,run,recon
from src.models.run import Run
from src.models.recon import Reconciliation
from src.services.calculation import calculate
from src.services.delivery import tick
from src.services.reconcile import execute,recover
Base.metadata.create_all(engine)
r=redis.Redis.from_url(REDIS_URL)
with Session() as db: recover(db,r)
loops=0
while True:
 Path('/tmp/worker-heartbeat').write_text(str(time.time()))
 try:
  item=r.lpop('report-jobs')
  if item:
   with Session() as db:
    job=db.get(Run,int(item))
    if job and job.status=='queued':
     job.status='running';db.commit()
     try: job.result=calculate(job.snapshot['sources'],job.snapshot['policy']);job.status='completed'
     except Exception as exc: job.status='failed';job.error=str(exc);traceback.print_exc()
     db.commit()
  item=r.lpop('recon-jobs')
  if item:
   with Session() as db:
    job=db.get(Reconciliation,int(item))
    if job and job.status=='queued': execute(db,job)
  with Session() as db: tick(db)
  loops+=1
  if loops%15==0:
   with Session() as db: recover(db,r)
 except Exception: traceback.print_exc()
 time.sleep(1)
