import {useEffect} from 'react';
import {LineChart,Line,XAxis,YAxis,Tooltip,ResponsiveContainer,CartesianGrid} from 'recharts';
import {api} from '../api/client';import {useApi} from '../hooks/useApi';import type {MapPoint} from '../types/api';
export default function ObservationHistory({city,metric}:{city:string;metric:string}){
 const history=useApi(()=>api<{provider:string;retrieved_at:string;points:MapPoint[]}[]>('workspace/history?city_id='+city),[city,metric]);
 useEffect(()=>{const timer=setInterval(history.reload,60000);return()=>clearInterval(timer)},[city,metric]);
 const records=(history.data??[]).filter(r=>r.provider===(metric==='pm25'?'air':'weather')).map(r=>{const p=r.points[0];return {time:p?.observed_at??r.retrieved_at,value:p?.readings[metric]?.value}}).filter(r=>r.value!==undefined).reverse();
 const rows=[...new Map(records.map(r=>[r.time,r])).values()];
 return <section className="panel"><div className="section-head"><h3>{metric==='pm25'?'PM2.5 · µg/m³':'Rainfall rate · mm/h'} · collected history</h3><span className="badge research">Live API model estimates</span></div>{history.error?<p className="error">{history.error}</p>:rows.length<2?<p>Collecting observations. A trend appears after two distinct provider timestamps; no historical points are invented.</p>:<div className="chart"><ResponsiveContainer><LineChart data={rows}><CartesianGrid stroke="var(--line)" vertical={false}/><XAxis dataKey="time" tickFormatter={v=>new Date(v).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})}/><YAxis/><Tooltip labelFormatter={v=>new Date(String(v)).toLocaleString('en-IN')}/><Line dataKey="value" stroke="var(--accent)" dot={false}/></LineChart></ResponsiveContainer></div>}<small>Up to 7 days retained locally. Observation timestamps are used on the time axis.</small></section>
}
