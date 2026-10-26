import {api} from './client';import type {Example,Prediction} from '../types/api';
export const getExample=(component:string)=>api<Example>('predictions/'+component+'/example');
export const predict=(component:string,body:unknown)=>api<Prediction>('predictions/'+component,body);
