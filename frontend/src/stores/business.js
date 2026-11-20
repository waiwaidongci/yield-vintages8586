import {loadAll} from '../api/business.js';
export const store={session:JSON.parse(localStorage.getItem('session')||'null'),data:{sources:[],periods:[],policies:[],runs:[],reconciliations:[],batches:[],schedules:[],deliveries:[],audits:[]},selected:null,selectedRecon:null};
export async function reload(){store.data=await loadAll()}
export function setSession(value){store.session=value;if(value)localStorage.setItem('session',JSON.stringify(value));else localStorage.removeItem('session')}
