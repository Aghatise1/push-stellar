const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/wallet-connect.js', 'utf8');

function harness(initialConnected, result) {
  const listeners = {};
  const nodes = Object.fromEntries(['chip','state','address','message','disconnect'].map(k => [k, {dataset:{},hidden:false}]));
  const shell = {
    dataset:{initialConnected:String(initialConnected),walletSyncEndpoint:'/wallet/sync/',savedAddress:'GSAVED'},
    querySelector(selector) { return nodes[selector.replace('[data-wallet-','').replace(']','')]; },
  };
  let reloads = 0;
  const window = {
    location:{reload(){reloads++;}},
    addEventListener(){},
    freighterApi:{
      async isConnected(){return {isConnected:true};},
      async getNetwork(){return {network:'TESTNET'};},
      async getAddress(){return {address:'GSAVED'};},
    },
  };
  const document = {
    cookie:'',
    querySelectorAll(){return [];},
    querySelector(selector) {
      if(selector==='[data-wallet-shell]') return shell;
      if(selector==='meta[name="csrf-token"]') return {content:'test-csrf'};
      return null;
    },
    addEventListener(name,fn){listeners[name]=fn;},
  };
  vm.runInNewContext(source,{window,document,Date,console,fetch:async()=>({
    ok:true,status:200,headers:{get(){return 'application/json';}},
    async text(){return JSON.stringify({ok:true,...result});},
  })});
  return {listeners,nodes,get reloads(){return reloads;}};
}

test('explicit server disconnection wins over an available extension', async()=>{
  const h=harness(false,{connected:false,state:'disconnected',savedAddress:'GSAVED'});
  h.listeners.DOMContentLoaded();
  await new Promise(setImmediate);
  assert.equal(h.nodes.disconnect.hidden,true);
  assert.match(h.nodes.chip.textContent,/^Saved /);
  assert.equal(h.reloads,0);
});

test('revoked connection refreshes server-rendered wallet controls', async()=>{
  const h=harness(true,{connected:false,state:'disconnected',savedAddress:'GSAVED'});
  h.listeners.DOMContentLoaded();
  await new Promise(setImmediate);
  assert.equal(h.nodes.state.textContent,'Freighter disconnected');
  assert.equal(h.reloads,1);
});

test('confirmed matching connection displays active controls without reload loops', async()=>{
  const h=harness(true,{connected:true,activeAddress:'GSAVED',savedAddress:'GSAVED'});
  h.listeners.DOMContentLoaded();
  await new Promise(setImmediate);
  assert.equal(h.nodes.disconnect.hidden,false);
  assert.equal(h.nodes.state.textContent,'Connected to Freighter');
  assert.equal(h.reloads,0);
});
