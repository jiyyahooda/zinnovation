import type {City} from '../types/api';
export default function CitySelector({cities,value,onChange}:{cities:City[];value:string;onChange:(v:string)=>void}){return <label className="city-selector"><span>City workspace</span><select aria-label="City" value={value} onChange={e=>onChange(e.target.value)}>{cities.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>}
