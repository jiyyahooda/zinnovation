import type {MapPoint} from '../../types/api';
export type MapController={focus:(point:[number,number],zoom:number)=>void};
export type CanvasProps={points:MapPoint[];center:[number,number];dark:boolean;trafficVisible:boolean;onSelect:(p:MapPoint)=>void;onReady:(controller:MapController|null)=>void;onFailure:(reason:string)=>void};
export const mapColors:Record<string,string>={weather:'#3da6da',air:'#38a875',traffic:'#f5ad32',reports:'#f05d62',assets:'#a391d4',scenario:'#ff6b00'};
