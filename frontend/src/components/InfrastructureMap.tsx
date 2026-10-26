import CascadeGraph from './CascadeGraph';import type {Graph} from '../types/api';
export default function InfrastructureMap({graph}:{graph:Graph}){return <><div className="notice">No verified municipal asset coordinates were supplied. This interactive schematic preserves the research asset IDs without placing them on a city map.</div><CascadeGraph graph={graph}/></>}
