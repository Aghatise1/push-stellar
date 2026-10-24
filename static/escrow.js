(function () {
  'use strict';
  var room = document.querySelector('[data-escrow-room]');
  if (!room) return;
  var status = room.querySelector('[data-escrow-status]');
  var retry = room.querySelector('[data-escrow-retry]');
  var token = null;
  var signedXdr = null;
  var busy = false;
  var stateVersion = room.dataset.stateVersion;
  function csrf() { var input = document.querySelector('[name=csrfmiddlewaretoken]'); return input ? input.value : ''; }
  async function post(url, payload) {
    var response = await fetch(url, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-CSRFToken':csrf()}, body:JSON.stringify(payload)});
    if (!response.headers.get('content-type')?.includes('application/json')) throw new Error('Session or service unavailable. Refresh and check transaction status before trying again.');
    var data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.message || 'The operation could not be completed.');
    return data;
  }
  async function check() {
    var result = await post(room.dataset.submit, {token:token, signedXdr:signedXdr});
    status.textContent = result.message;
    if (result.redirectUrl) window.location.assign(result.redirectUrl);
    return result.pending;
  }
  async function perform(form) {
    var api = window.freighterApi;
    if (!api) throw new Error('Install and unlock Freighter, then connect your testnet wallet.');
    var network = await api.getNetwork();
    if (network.error || network.network !== 'TESTNET') throw new Error('Switch Freighter to Stellar testnet.');
    var address = await api.getAddress();
    if (address.error || !address.address) throw new Error('Connect your wallet before continuing.');
    var payload = Object.fromEntries(new FormData(form)); payload.action = form.dataset.escrowAction;
    var prepared = await post(room.dataset.prepare, payload);
    token = prepared.token; retry.hidden = false;
    if (address.address !== prepared.source) throw new Error('Switch to the wallet named in this agreement. The unsigned request expires after five minutes.');
    status.textContent = prepared.message + ' Review the exact operation in Freighter.';
    var signed = await api.signTransaction(prepared.xdr, {networkPassphrase:prepared.networkPassphrase, address:prepared.source});
    if (signed.error || !signed.signedTxXdr) throw new Error('Wallet approval was cancelled or failed. No signed transaction was submitted. The request expires after five minutes.');
    signedXdr = signed.signedTxXdr;
    for (var i=0; i<8; i++) { if (!await check()) return; await new Promise(function(resolve) { window.setTimeout(resolve,2500); }); }
    status.textContent = 'Still awaiting confirmation. Use Check transaction status; do not sign a second payment.';
  }
  async function run(task) {
    if (busy) return; busy = true;
    var buttons = Array.from(room.querySelectorAll('button'));
    var original = buttons.map(function(button) { return button.disabled; });
    buttons.forEach(function(button) { button.disabled = true; });
    status.textContent = 'Checking Stellar testnet…';
    try { await task(); } catch(error) { status.textContent = error.message || 'Confirmation unavailable. Check status before sending again.'; }
    finally { busy = false; buttons.forEach(function(button,index) { button.disabled = original[index]; }); }
  }
  room.querySelectorAll('[data-escrow-action]').forEach(function(form) { form.addEventListener('submit',function(event) { event.preventDefault(); run(function() { return perform(form); }); }); });
  room.querySelectorAll('[data-escrow-check]').forEach(function(button) { button.addEventListener('click',function() { token = button.dataset.escrowCheck; run(check); }); });
  retry.addEventListener('click',function() { run(check); });
  async function syncState() {
    if (busy || document.visibilityState !== 'visible' || !room.dataset.stateUrl) return;
    try {
      var response = await fetch(room.dataset.stateUrl, {credentials:'same-origin', cache:'no-store'});
      if (!response.ok) return;
      var data = await response.json();
      if (data.version && data.version !== stateVersion) window.location.reload();
    } catch (error) {
      // A transient status check must never interrupt a wallet action.
    }
  }
  window.setInterval(syncState, 5000);
  var assistant = document.querySelector('[data-orbio-room]');
  if (assistant) {
    var assistantForm=assistant.querySelector('[data-orbio-form]');
    var assistantResult=assistant.querySelector('[data-orbio-result]');
    assistantForm.addEventListener('submit',async function(event) {
      event.preventDefault();assistantResult.textContent='Preparing an advisory draft…';
      try {
        var data=await post(assistant.dataset.orbioUrl,Object.fromEntries(new FormData(assistantForm)));
        var result=data.result;
        var lines=[result.summary].concat(result.observations||[],result.missing_information||[],[result.suggested_next_step]);
        if(result.escalate_to_human) lines.push('Human review is required.');
        assistantResult.textContent=lines.filter(Boolean).join(' ');
      } catch(error) {assistantResult.textContent=error.message||'The advisory draft is unavailable.';}
    });
  }
})();
