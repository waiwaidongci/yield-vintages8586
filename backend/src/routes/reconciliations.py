from fastapi import APIRouter,Depends,HTTPException
from src.config.database import database
from src.controllers.auth import current,editor
from src.models.run import Run
from src.models.recon import Reconciliation
from src.schemas.requests import ReconInput
from src.services.reconcile import submit,retry
from src.utils.serialize import row
router=APIRouter()
@router.get('/reconciliations')
def reconciliations(db=Depends(database),u=Depends(current)): return [row(x) for x in db.query(Reconciliation).order_by(Reconciliation.id.desc()).all()]
@router.post('/reconciliations')
def create(b:ReconInput,db=Depends(database),u=Depends(editor)): return row(submit(db,u,b))
@router.get('/reconciliations/{id}')
def detail(id:int,db=Depends(database),u=Depends(current)):
 obj=db.get(Reconciliation,id)
 if not obj: raise HTTPException(404,'核账单不存在')
 return row(obj)
@router.post('/reconciliations/{id}/retry')
def again(id:int,db=Depends(database),u=Depends(editor)): return row(retry(db,u,id))
@router.get('/batches')
def batches(db=Depends(database),u=Depends(current)):
 stats={}
 for r in db.query(Run).filter(Run.approved==True,Run.status=='completed').order_by(Run.id).all():
  seen=set()
  for s in (r.snapshot or {}).get('sources') or []:
   b=s.get('batch')
   if isinstance(b,str) and b.strip() and b not in seen: seen.add(b);stats.setdefault(b,[]).append(r.id)
 return [{'batch':b,'reports':len(ids),'run_ids':ids} for b,ids in sorted(stats.items())]
