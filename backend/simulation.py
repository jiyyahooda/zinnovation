"""Use the existing trained flood surrogate on explicitly synthetic inputs."""
from src.civicflux.integration import fixture
from src.civicflux.serving import serve
from project_paths import PROJECT_ROOT

def simulate(inputs,clock,engine='mass_balance'):
    if engine=='mass_balance':
        import pandas as pd
        from civicflux_core import simulate_depth
        depth=float(simulate_depth(pd.DataFrame([inputs]))[0])
        return {'status':'supported_simulation','component':'flood_mass_balance','model_version':None,
            'prediction':[{'depth_m':depth,'scenario_alert':depth>=.15,'synthetic':True}],
            'uncertainty':None,'units':'m','horizon':'uniform storm duration, not a real-time forecast',
            'geographic_scope':'hypothetical catchment','research_only':True,'dispatch_allowed':False,
            'warnings':['Existing civicflux_core.simulate_depth mass-balance simulator; no trained model used.',
                'No calibrated topography, backwater, routing or real municipal validation. Uncertainty unavailable.']}
    request=fixture('flood',PROJECT_ROOT)
    request.update(scenarios=[inputs],observation_time=clock,as_of=clock)
    return serve('flood',request,PROJECT_ROOT)
