import {api} from './client';import type {Observations} from '../types/api';
export const getObservations=(city:string)=>api<Observations>('observations?city_id='+encodeURIComponent(city));
