import {api} from './client';import type {Scenario,ScenarioInput,Complaint,Feedback} from '../types/api';
export const getScenarios=()=>api<Scenario[]>('scenarios');
export const runScenario=(input:ScenarioInput)=>api<Scenario>('scenarios',input);
export const getComplaints=()=>api<Complaint[]>('complaints');
export const getFeedback=()=>api<Feedback>('feedback');
