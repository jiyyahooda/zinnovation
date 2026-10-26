import type {ScenarioInput} from './types/api';
type Store=Pick<Storage,'getItem'|'setItem'>;
const key=(city:string)=>'civicflux-draft-v1-'+city;
export function readDraft(store:Store,city:string):ScenarioInput|null{
 try{const value=JSON.parse(store.getItem(key(city))||'null');if(!value||typeof value.name!=='string'||!Array.isArray(value.initial)||!value.flood||!value.resources?.crew_hours||typeof value.load!=='number'||!['mass_balance','trained_surrogate'].includes(value.flood_engine))return null;return value}catch{return null}
}
export function saveDraft(store:Store,city:string,value:ScenarioInput):boolean{try{store.setItem(key(city),JSON.stringify(value));return true}catch{return false}}
