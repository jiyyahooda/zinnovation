import {ComposedChart,Area,Line,XAxis,YAxis,Tooltip,ResponsiveContainer,CartesianGrid} from 'recharts';
import {api} from '../api/client';import {useApi} from '../hooks/useApi';
type Row={target_time:string;entity:string;target:number;prediction:number;lower:number;upper:number};
export default function ForecastChart({component}:{component:string}){
 const supported=['rainfall','aqi','traffic'].includes(component);
 const source=useApi(()=>supported?api<{kind:string;rows:Row[]}>('predictions/'+component+'/series'):Promise.resolve({kind:'unavailable',rows:[]}),[component]);
 if(!supported)return null;
 const unit=component==='rainfall'?'mm/day':component==='aqi'?'PM2.5 ug/m3':'vehicles/hour';
 const rows=source.data?.rows.filter(r=>r.entity===source.data?.rows[0]?.entity).map(r=>({...r,interval:[r.lower,r.upper]}))??[];
 return <section className="panel"><h3>Saved holdout evaluation · {unit}</h3><p>Archived observations, rolling predictions, and saved 90% residual intervals. Coverage is not guaranteed for a particular case. These results are not live inference.</p>{source.error?<div className="error">{source.error}</div>:source.loading?<p>Loading saved research evaluation…</p>:<div className="chart"><ResponsiveContainer><ComposedChart data={rows}><CartesianGrid vertical={false} stroke="var(--line)"/><XAxis dataKey="target_time" tickFormatter={v=>String(v).slice(5,16)} stroke="var(--muted)" minTickGap={45}/><YAxis stroke="var(--muted)" width={45}/><Tooltip/><Area type="monotone" dataKey="interval" name="90% saved interval" fill="var(--accent)" fillOpacity={.12} stroke="none"/><Line type="monotone" dataKey="target" name="Observed" stroke="var(--muted)" dot={false}/><Line type="monotone" dataKey="prediction" name="Research prediction" stroke="var(--accent)" dot={false}/></ComposedChart></ResponsiveContainer></div>}</section>;
}
