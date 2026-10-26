// Contract checks for geographic filtering and distinct flood output types.
const fs=require('node:fs'),ts=require('typescript'),assert=require('node:assert/strict');process.chdir(__dirname);
const box={exports:{}};const code=ts.transpileModule(fs.readFileSync('src/municipal/domain.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
new Function('require','module','exports',code)(require,box,box.exports);
const {currentPoints,matchesIssue,indianAqi,floodSummary,reportOnPoint}=box.exports;
const w={points:[{id:'wx',layer:'weather',kind:'modeled_weather'},{id:'pm',layer:'air',kind:'modeled_air_quality'},{id:'rd',layer:'traffic',kind:'provider_current_traffic'}],reported_points:[{id:'r1',report_id:'r1',layer:'reports',category:'water',kind:'reported_incident'}],asset_points:[],synthetic_points:[{id:'s',kind:'synthetic_scenario'}]};
assert.equal(currentPoints(w).length,4);
assert.deepEqual(currentPoints(w).filter(p=>matchesIssue(p,'Water Supply')).map(p=>p.id),['r1']);
assert.deepEqual(currentPoints(w).filter(p=>matchesIssue(p,'Air Quality')).map(p=>p.id),['pm']);
assert.equal(reportOnPoint(w.reported_points[0]),'r1');
assert.equal(indianAqi({...w,indian_aqi:{status:'unavailable',value:130,category:'Moderate'}}).value,null);
assert.deepEqual(floodSummary({flood:{prediction:[{depth_m:.42}]}}),{depth:.42,score:null});
assert.deepEqual(floodSummary({flood:{prediction:[{simulated_flood_probability:.7}]}}),{depth:null,score:.7});
assert.deepEqual(floodSummary({flood:{prediction:null}}),{depth:null,score:null});
assert.deepEqual(floodSummary({flood:{prediction:{depth_m:NaN}}}),{depth:null,score:null});
console.log('Municipal geography, report identity, AQI abstention and flood-output checks passed');
