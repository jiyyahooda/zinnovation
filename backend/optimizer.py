from src.civicflux.optimization import solve_cpsat,greedy_allocate,DEFAULT_WEIGHTS,validate_weights

def plan(cases,resources,weights=None):
    weights=validate_weights(weights or DEFAULT_WEIGHTS)
    results={'CP-SAT':solve_cpsat(cases,resources,weights), 'utility_greedy':greedy_allocate(cases,resources,'utility',weights), 'severity_greedy':greedy_allocate(cases,resources,'severity',weights)}
    explanations=[]
    for case in cases:
        breakdown={k:weights[k]*case[k]*(-1 if k=='carbon_penalty' else 1) for k in weights}
        explanations.append({**case,'score_breakdown':breakdown,'utility':sum(breakdown.values())})
    return {'comparisons':results,'candidates':explanations,'weights':weights,'constraints':['Shared hypothetical budget','Crew hours per skill','Pump availability','Each candidate selected at most once'],'dispatch_allowed':False}
