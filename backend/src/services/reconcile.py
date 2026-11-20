import hashlib,json,time
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from src.models.run import Run
from src.models.recon import Reconciliation
from src.models.source import Policy
from src.services.audit import log
from src.services.setcover import solve_cover,NoSolution,Unproven
from src.services.validation import validate_policy
from src.config.settings import REDIS_URL
import redis
BASE_KEYS=('input','first_pass','reworked_good','scrap')
SOLVE_LIMIT=30.0
def key_of(name,batches,policy_id):
 return hashlib.sha256(json.dumps({'name':name,'batches':sorted(set(batches)),'policy_id':policy_id},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def freeze(db):
 """排队时冻结候选与口径：仅已复核且完成的报告可参选；缺批号或同批底数内部不一致的不参选。"""
 candidates=[];excluded=[]
 runs=db.query(Run).filter(Run.approved==True,Run.status=='completed').order_by(Run.id).all()
 for r in runs:
  batches={};conflict=False
  for s in (r.snapshot or {}).get('sources') or []:
   b=(s.get('batch') or '').strip() if isinstance(s.get('batch'),str) else None
   if not b:continue
   base=[int(s[k]) for k in BASE_KEYS]
   if b in batches and batches[b]!=base:conflict=True;break
   batches[b]=base
  if not batches:excluded.append({'run_id':r.id,'name':r.name,'reason':'缺批号，旧报告可查但不参选'})
  elif conflict:excluded.append({'run_id':r.id,'name':r.name,'reason':'同批底数内部不一致，不参选'})
  else:candidates.append({'run_id':r.id,'name':r.name,'checksum':r.checksum,'batches':batches})
 return candidates,excluded
def submit(db,user,body):
 policy=db.get(Policy,body.policy_id)
 if not policy:raise HTTPException(404,'口径版本不存在')
 batches=sorted({b.strip() for b in body.batches if b and b.strip()})
 if not batches:raise HTTPException(422,'请至少指定一个批号')
 if any(len(b)>120 for b in batches):raise HTTPException(422,'批号过长')
 key=key_of(body.name,batches,body.policy_id)
 existing=db.query(Reconciliation).filter_by(request_key=key).first()
 if existing:return existing
 candidates,excluded=freeze(db)
 snapshot={'name':body.name,'batches':batches,'policy':policy.data,'candidates':candidates}
 checksum=hashlib.sha256(json.dumps(snapshot,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
 obj=Reconciliation(name=body.name,request_key=key,status='queued',batches=batches,policy=policy.data,candidates=candidates,excluded=excluded,checksum=checksum,created=time.time())
 db.add(obj);log(db,user.email,'recon.queue',body.name)
 try:db.commit()
 except IntegrityError:
  db.rollback();return db.query(Reconciliation).filter_by(request_key=key).first()
 redis.Redis.from_url(REDIS_URL).rpush('recon-jobs',obj.id)
 return obj
def recompute(selected,targets,policy):
 """按冻结口径重算：每批计一次并保留出处；汇总按分母加权，不做简单平均。"""
 validate_policy(policy);rows=[];n=d=0
 for b in sorted(targets):
  holders=[s for s in selected if b in s['bases']]
  src=min(holders,key=lambda x:x['run_id']);inp,fp,rw,sc=src['bases'][b]
  num=fp if policy['numerator']=='first_pass' else fp+rw
  den=inp if policy['denominator']=='input' else inp-sc
  if den<=0:raise ValueError('口径分母为0：批号'+b)
  n+=num;d+=den
  rows.append({'批号':b,'出处报告':'#'+str(src['run_id'])+' '+src['name'],'投入数':inp,'一次通过数':fp,'返工合格数':rw,'报废数':sc,'分子':num,'分母':den,'良率':num/den,'重复覆盖':len(holders)})
 summary={'批次数':len(targets),'分子合计':n,'分母合计':d,'加权良率':n/d if d else 0,'口径版本':policy['version'],'选用报告数':len(selected)}
 return rows,summary
def execute(db,job):
 job.status='running';job.started=time.time();db.commit()
 try:
  solved=solve_cover(job.candidates,job.batches,limit=SOLVE_LIMIT)
  rows,summary=recompute(solved['selected'],job.batches,job.policy)
  job.result={'summary':summary,'rows':rows,
   'reports':[{'run_id':s['run_id'],'name':s['name']}for s in sorted(solved['selected'],key=lambda x:x['run_id'])],
   'proof':{'结论':'已证最优（穷举搜索）','选用报告数':solved['depth'],'搜索节点':solved['nodes'],'用时秒':round(solved['elapsed'],3),'冻结候选数':len(job.candidates),'参与搜索数':solved['searched']},
   'method':'候选与口径在排队时冻结，之后的复核不改变本单。以批号为键校验同批底数一致（冲突组合不可同选），分支搜索最少报告份数并穷举证最优；每批按冻结口径计一次，汇总率=分子合计/分母合计，不做简单平均。',
   'warnings':['缺批号的旧报告不参与候选。','同批底数不一致的报告组合已被排除；同批多报告覆盖时按一致底数去重，每批仅计一次。','30秒内未证最优或无解即拒绝发布。']}
  job.status='completed'
 except NoSolution as exc:job.status='failed';job.error='无解：'+str(exc)
 except Unproven as exc:job.status='failed';job.error='未证最优：'+str(exc)
 except Exception as exc:job.status='failed';job.error='核算异常：'+str(exc)
 job.finished=time.time();log(db,'worker','recon.'+job.status,job.id);db.commit()
def recover(db,r):
 """中断恢复：排队丢失或运行超窗的核账单重新入队；重复入队无害（worker仅处理queued）。"""
 now=time.time()
 for j in db.query(Reconciliation).filter(Reconciliation.status.in_(('queued','running'))).all():
  if j.status=='running' and j.started and now-j.started<90:continue
  if j.status=='queued' and j.created and now-j.created<30:continue
  j.status='queued';j.started=None
  r.rpush('recon-jobs',j.id);log(db,'worker','recon.recover',j.id)
 db.commit()
def retry(db,user,id):
 obj=db.get(Reconciliation,id)
 if not obj:raise HTTPException(404,'核账单不存在')
 if obj.status!='failed':raise HTTPException(409,'仅失败单据可重新排队')
 obj.status='queued';obj.error=None;obj.result=None;obj.started=None;obj.finished=None
 log(db,user.email,'recon.retry',id);db.commit()
 redis.Redis.from_url(REDIS_URL).rpush('recon-jobs',obj.id)
 return obj
