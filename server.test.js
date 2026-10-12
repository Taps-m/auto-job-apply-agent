const {test}=require('node:test');
const assert=require('node:assert/strict');
const {metrics,eligibility}=require('./server');
test('queued or unconfirmed responses do not inflate submission conversion',()=>{assert.deepEqual(metrics([{status:'Queued'},{status:'Recruiter response'},{submittedAt:'2026-10-12',status:'Interview'},{submittedAt:'2026-10-12',status:'Rejected'}]),{submitted:2,responses:1,interviews:1,responseRate:50});});
test('no submissions yields unavailable response rate',()=>assert.equal(metrics([]).responseRate,null));
test('salary filter handles undisclosed salaries independently',()=>{const p={minimumCTCLPA:25,allowUnknownSalary:true};assert.equal(eligibility({ctcLPA:24},p),'Below salary minimum');assert.match(eligibility({ctcLPA:null},p),/verification/);assert.equal(eligibility({ctcLPA:null},{...p,allowUnknownSalary:false}),'Salary unknown');});
