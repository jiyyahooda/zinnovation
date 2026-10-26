import type {Model} from '../types/api';
export default function ModelStatus({model}:{model:Model}){return <article className="model-row"><div><strong>{model.component.replaceAll('_',' ')}</strong><small>{model.selected_model} · {model.version}</small></div><span className={'badge '+(model.readiness==='Not ready'?'muted':'research')}>{model.readiness}</span></article>}
