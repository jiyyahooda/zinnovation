import InfrastructureMap from '../components/InfrastructureMap';import type {Graph} from '../types/api';
export default function Infrastructure({graph}:{graph:Graph|null}){return graph?<InfrastructureMap graph={graph}/>:<p>Loading infrastructure graph…</p>}
