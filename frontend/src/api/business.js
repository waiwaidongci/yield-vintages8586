import {request} from './client.js';
export const loadAll=async()=>Object.fromEntries(await Promise.all(['sources','periods','policies','runs','reconciliations','batches','schedules','deliveries','audits'].map(async k=>[k,await request('/'+k)])));
export const saveSource=(data,id)=>request('/sources'+(id?'/'+id:''),id?'PUT':'POST',{data});
export const savePolicy=data=>request('/policies','POST',{data});
export const submitRun=data=>request('/runs','POST',data);
export const approveRun=(id,note)=>request('/runs/'+id+'/approve','POST',{note});
export const submitRecon=data=>request('/reconciliations','POST',data);
export const retryRecon=id=>request('/reconciliations/'+id+'/retry','POST',{});
