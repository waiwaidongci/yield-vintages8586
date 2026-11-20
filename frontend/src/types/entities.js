// API实体字段约定：来源{id,natural_key,data}、口径{id,version,data}、报告{id,status,snapshot,checksum,result,approved}、核账{id,request_key,status,batches,policy,candidates,excluded,result,error}、计划{next_at,enabled}。
export const ENTITY_KEYS=['sources','policies','runs','reconciliations','schedules','deliveries'];
