import time,math
class NoSolution(Exception):pass
class Unproven(Exception):pass
def solve_cover(candidates,targets,limit=30.0,clock=time.monotonic):
 """精确最少报告集合覆盖：同批底数冲突的报告不可同选；限时内穷举证最优。
 candidates:[{'run_id','name','batches':{批号:[input,first_pass,reworked_good,scrap]}}]
 返回{'selected':[候选...],'nodes','elapsed','depth','searched'}；无解/未证最优抛异常。"""
 start=clock();deadline=start+limit;state={'nodes':0,'best':None}
 targets=set(targets)
 if not targets:raise NoSolution('未指定批号')
 reps={}
 for c in sorted(candidates,key=lambda x:x['run_id']):
  key=frozenset((b,tuple(v))for b,v in c['batches'].items())
  if key in reps:continue
  cover=set(c['batches'])&targets
  if not cover:continue
  reps[key]={'run_id':c['run_id'],'name':c['name'],'cover':cover,'bases':{b:tuple(v)for b,v in c['batches'].items()}}
 items=sorted(reps.values(),key=lambda x:(-len(x['cover']),x['run_id']))
 union=set().union(*(i['cover']for i in items))if items else set()
 missing=targets-union
 if missing:raise NoSolution('已复核候选报告未覆盖批号：'+'、'.join(sorted(missing)))
 def tick():
  if clock()>=deadline:raise Unproven('30秒时限内未能穷举证最优')
 def rec(pos,chosen,covered,bases,cap):
  state['nodes']+=1
  if state['nodes']%256==0:tick()
  if targets<=covered:state['best']=list(chosen);return True
  remaining=targets-covered
  maxcov=max((len(it['cover']&remaining)for it in items[pos:]),default=0)
  if maxcov==0 or len(chosen)+math.ceil(len(remaining)/maxcov)>cap:return False
  for i in range(pos,len(items)):
   it=items[i];newcov=it['cover']-covered
   if not newcov:continue
   if any(b in bases and bases[b]!=v for b,v in it['bases'].items()):continue
   added=[b for b in it['bases']if b not in bases]
   for b in added:bases[b]=it['bases'][b]
   chosen.append(i);covered|=it['cover']
   if rec(i+1,chosen,covered,bases,cap):return True
   chosen.pop();covered-=newcov
   for b in added:del bases[b]
  return False
 for k in range(1,len(items)+1):
  tick()
  if rec(0,[],set(),{},k):
   return{'selected':[items[i]for i in state['best']],'nodes':state['nodes'],'elapsed':clock()-start,'depth':k,'searched':len(items)}
 raise NoSolution('候选报告的同批底数互相冲突，任何组合都无法一致覆盖指定批号')
