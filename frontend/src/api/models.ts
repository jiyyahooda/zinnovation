import {api} from './client';import type {Model} from '../types/api';
export const getModels=()=>api<Model[]>('models');
