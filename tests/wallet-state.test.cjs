const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/wallet-connect.js', 'utf8');

const SAVED_ADDRESS = 'GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5';
const OTHER_ADDRESS = 'GCZJM35NKGVK47BB4SPBDV25477PZYIYPVVG453LPYFNXLS3FGHDXOCM';

function createHarness(options = {}) {
  const docListeners = {};
  const winListeners = {};
  const requests = [];
  const timeouts = [];
  const storageWrites = [];
  let now = options.now || 100000;
  let reloads = 0;

  const nodes = Object.fromEntries(
    ['chip', 'state', 'address', 'message', 'disconnect'].map(k => [
      k,
      { dataset: {}, hidden: false, textContent: '' },
    ])
  );
  const statusNode = { dataset: {}, hidden: true, textContent: '' };
  const toastNode = {
    className: 'wallet-toast',
    dataset: {},
    hidden: true,
    textContent: '',
    setAttribute() {},
  };
  const connectButton = {
    dataset: { walletEndpoint: '/wallet/connect/' },
    disabled: false,
    attributes: {},
    setAttribute(name, value) { this.attributes[name] = value; },
    removeAttribute(name) { delete this.attributes[name]; },
  };
  const disconnectForm = {
    action: '/wallet/disconnect/',
    dataset: { walletDisconnect: '' },
    hidden: !options.initialConnected,
  };
  const staffConnectControl = { dataset: {}, hidden: Boolean(options.initialConnected) };
  const staffWalletStatus = {
    dataset: {},
    textContent: options.initialConnected ? `Connected · ${SAVED_ADDRESS}` : 'Disconnected',
  };
  const paymentStatusNode = {
    dataset: {},
    hidden: true,
    textContent: '',
    children: [],
    appendChild(child) { this.children.push(child); },
  };
  const paymentSubmitButton = {
    disabled: false,
    textContent: 'Send payment',
    attributes: {},
    setAttribute(name, value) { this.attributes[name] = value; },
    removeAttribute(name) { delete this.attributes[name]; },
  };
  const paymentForm = {
    dataset: {
      prepareEndpoint: '/wallet/prepare/',
      submitEndpoint: '/wallet/submit/',
    },
    parentElement: {
      querySelector(selector) {
        return selector === '[data-payment-status]' ? paymentStatusNode : null;
      },
    },
    querySelector(selector) {
      return selector === 'button[type="submit"]' ? paymentSubmitButton : null;
    },
  };

  const shell = {
    dataset: {
      initialConnected: String(Boolean(options.initialConnected)),
      walletConnectEndpoint: '/wallet/connect/',
      walletSyncEndpoint: '/wallet/sync/',
      walletDisconnectEndpoint: '/wallet/disconnect/',
      savedAddress: options.savedAddress !== undefined ? options.savedAddress : SAVED_ADDRESS,
    },
    querySelector(selector) {
      return nodes[selector.replace('[data-wallet-', '').replace(']', '')] || null;
    },
  };

  const defaultFreighter = {
    async isConnected() { return { isConnected: true }; },
    async requestAccess() { return { address: SAVED_ADDRESS }; },
    async setAllowed() { return { isAllowed: true }; },
    async getNetwork() { return { network: 'TESTNET' }; },
    async getAddress() { return { address: SAVED_ADDRESS }; },
    async signTransaction() { return { signedTxXdr: 'SIGNED_XDR' }; },
  };

  const window = {
    location: {
      reload() { reloads++; },
      assign() {},
    },
    addEventListener(name, fn) { winListeners[name] = fn; },
    setTimeout(fn, delay) { timeouts.push({ fn, delay }); return timeouts.length; },
    freighterApi: options.freighterApi === null
      ? null
      : { ...defaultFreighter, ...(options.freighterApi || {}) },
    localStorage: {
      setItem(k, v) { storageWrites.push(['localStorage', k, v]); },
      getItem() { return null; },
    },
    sessionStorage: {
      setItem(k, v) { storageWrites.push(['sessionStorage', k, v]); },
      getItem() { return null; },
    },
  };

  const document = {
    hidden: false,
    cookie: '',
    body: {
      appendChild() {},
    },
    createElement() {
      return {
        className: '',
        dataset: {},
        hidden: false,
        setAttribute() {},
      };
    },
    querySelectorAll(selector) {
      if (selector === '[data-wallet-status]') return [statusNode];
      if (selector === '[data-wallet-connect]') return [connectButton];
      if (selector === '[data-wallet-disconnect]') return [nodes.disconnect, disconnectForm];
      if (selector === '[data-staff-connect-control]') return [staffConnectControl];
      if (selector === '[data-staff-wallet-status]') return [staffWalletStatus];
      return [];
    },
    querySelector(selector) {
      if (selector === '[data-wallet-shell]') return shell;
      if (selector === 'meta[name="csrf-token"]') return { content: 'test-csrf' };
      if (selector === '.wallet-toast') return toastNode;
      return null;
    },
    addEventListener(name, fn) { docListeners[name] = fn; },
  };

  let responder = options.responder || (async () => {
    if (options.result) {
      return { status: 200, body: { ok: true, ...options.result } };
    }
    return { status: 200, body: { ok: true, connected: false, state: 'disconnected', savedAddress: SAVED_ADDRESS } };
  });

  async function fetch(url, init = {}) {
    const parsedBody = init.body ? JSON.parse(init.body) : {};
    requests.push({ url, method: init.method || 'GET', headers: init.headers || {}, body: parsedBody, rawBody: init.body || '' });
    const reply = await responder(url, parsedBody, init);
    const status = reply.status || 200;
    const payload = reply.body || { ok: true };
    return {
      ok: status >= 200 && status < 300,
      status,
      redirected: Boolean(reply.redirected),
      headers: {
        get(name) {
          return String(name).toLowerCase() === 'content-type' ? (reply.contentType || 'application/json') : '';
        },
      },
      async text() {
        return typeof payload === 'string' ? payload : JSON.stringify(payload);
      },
    };
  }

  class MockFormData {
    constructor() {}
    forEach(cb) {
      cb('XLM', 'asset');
      cb('10', 'amount');
    }
  }

  const CustomDate = {
    now() { return now; },
  };

  vm.runInNewContext(source, {
    window,
    document,
    Date: CustomDate,
    FormData: MockFormData,
    console,
    fetch,
    setTimeout: window.setTimeout,
  });

  async function flush() {
    for (let i = 0; i < 6; i++) {
      await new Promise(setImmediate);
    }
  }

  return {
    window,
    document,
    shell,
    nodes,
    statusNode,
    toastNode,
    connectButton,
    disconnectForm,
    staffConnectControl,
    staffWalletStatus,
    paymentForm,
    paymentStatusNode,
    paymentSubmitButton,
    requests,
    timeouts,
    storageWrites,
    docListeners,
    winListeners,
    get reloads() { return reloads; },
    advanceTime(ms) { now += ms; },
    setResponder(fn) { responder = fn; },
    async triggerDOMContentLoaded() {
      docListeners.DOMContentLoaded();
      await flush();
    },
    async triggerFocus() {
      winListeners.focus();
      await flush();
    },
    async triggerVisibilityChange(hidden = false) {
      document.hidden = hidden;
      docListeners.visibilitychange();
      await flush();
    },
    async clickConnect() {
      let prevented = false;
      docListeners.click({
        target: {
          closest(selector) {
            return selector === '[data-wallet-connect]' ? connectButton : null;
          },
        },
        preventDefault() { prevented = true; },
      });
      await flush();
      return prevented;
    },
    async submitDisconnect() {
      let prevented = false;
      docListeners.submit({
        target: {
          closest(selector) {
            return selector === '[data-wallet-disconnect]' ? disconnectForm : null;
          },
        },
        preventDefault() { prevented = true; },
      });
      await flush();
      return prevented;
    },
    async submitPayment() {
      let prevented = false;
      docListeners.submit({
        target: {
          closest(selector) {
            if (selector === '[data-wallet-disconnect]') return null;
            return selector === '[data-stellar-payment]' ? paymentForm : null;
          },
        },
        preventDefault() { prevented = true; },
      });
      await flush();
      return prevented;
    },
  };
}

// 1. Freighter is unavailable or not installed
test('1. Freighter unavailable or not installed gives clear installation guidance without calling server connect', async () => {
  const missingApi = createHarness({ freighterApi: null });
  await missingApi.clickConnect();
  assert.equal(missingApi.statusNode.dataset.state, 'error');
  assert.equal(
    missingApi.statusNode.textContent,
    'Freighter could not load. Open Push in Chrome or Edge with Freighter installed, then try again.'
  );
  assert.equal(missingApi.requests.length, 0);
  assert.equal(missingApi.connectButton.disabled, false);

  const notInstalled = createHarness({
    freighterApi: {
      async isConnected() { return { isConnected: false }; },
    },
  });
  await notInstalled.clickConnect();
  assert.equal(notInstalled.statusNode.dataset.state, 'error');
  assert.equal(
    notInstalled.statusNode.textContent,
    'Freighter is not available in this browser. Open Push in Chrome or Edge with the extension installed, or enter a public testnet address manually.'
  );
  assert.equal(notInstalled.requests.length, 0);
});

// 2. Freighter is locked or declines access
test('2. Freighter locked or declining access reports accurate approval or unlock message', async () => {
  const declined = createHarness({
    freighterApi: {
      async requestAccess() {
        return { address: '', error: 'Wallet access was not approved in Freighter.' };
      },
    },
  });
  await declined.clickConnect();
  assert.equal(declined.statusNode.dataset.state, 'error');
  assert.equal(declined.statusNode.textContent, 'Wallet access was not approved in Freighter.');
  assert.equal(declined.requests.length, 0);

  const legacyDeclined = createHarness({
    freighterApi: {
      requestAccess: undefined,
      async setAllowed() { return { isAllowed: false }; },
    },
  });
  await legacyDeclined.clickConnect();
  assert.equal(legacyDeclined.statusNode.dataset.state, 'error');
  assert.equal(legacyDeclined.statusNode.textContent, 'Wallet access was not approved in Freighter.');
  assert.equal(legacyDeclined.requests.length, 0);

  const locked = createHarness({
    freighterApi: {
      async requestAccess() { return { address: '' }; },
    },
  });
  await locked.clickConnect();
  assert.equal(locked.statusNode.dataset.state, 'error');
  assert.equal(locked.statusNode.textContent, 'Freighter did not return a public address. Unlock it and try again.');
  assert.equal(locked.requests.length, 0);
});

// 3. Freighter is connected to the wrong network
test('3. Freighter connected to the wrong network shows wrong network state and blocks connection', async () => {
  const h = createHarness({
    initialConnected: false,
    freighterApi: {
      async getNetwork() { return { network: 'PUBLIC' }; },
      async getAddress() { return { address: SAVED_ADDRESS }; },
    },
    responder: async (url, body) => {
      if (url === '/wallet/sync/') {
        assert.equal(body.network, 'PUBLIC');
        return {
          status: 200,
          body: {
            ok: true,
            connected: false,
            state: 'wrong_network',
            message: 'Freighter is connected to another network. Switch it to Stellar testnet.',
            savedAddress: SAVED_ADDRESS,
            activeAddress: SAVED_ADDRESS,
          },
        };
      }
      if (url === '/wallet/connect/') {
        return {
          status: 400,
          body: {
            ok: false,
            message: 'Switch Freighter to Stellar testnet and try again.',
          },
        };
      }
      throw new Error(`Unexpected URL: ${url}`);
    },
  });

  await h.triggerDOMContentLoaded();
  assert.equal(h.nodes.state.dataset.state, 'wrong_network');
  assert.equal(h.nodes.state.textContent, 'Wrong Stellar network');
  assert.equal(h.nodes.message.textContent, 'Freighter is connected to another network. Switch it to Stellar testnet.');
  assert.equal(h.nodes.disconnect.hidden, true);

  await h.clickConnect();
  assert.equal(h.statusNode.dataset.state, 'error');
  assert.equal(h.statusNode.textContent, 'Switch Freighter to Stellar testnet and try again.');
  assert.equal(h.nodes.state.dataset.state, 'wrong_network');
  assert.equal(h.nodes.disconnect.hidden, true);
});

// 4. The active Freighter account differs from the saved Push address
test('4. Active Freighter account differing from saved Push address displays mismatch warning', async () => {
  const h = createHarness({
    initialConnected: false,
    freighterApi: {
      async getAddress() { return { address: OTHER_ADDRESS }; },
      async getNetwork() { return { network: 'TESTNET' }; },
    },
    responder: async (url, body) => {
      assert.equal(url, '/wallet/sync/');
      assert.equal(body.address, OTHER_ADDRESS);
      return {
        status: 200,
        body: {
          ok: true,
          connected: false,
          state: 'mismatch',
          message: 'Freighter changed accounts. Reconnect to use the active account in Push.',
          activeAddress: OTHER_ADDRESS,
          savedAddress: SAVED_ADDRESS,
        },
      };
    },
  });

  await h.triggerDOMContentLoaded();
  assert.equal(h.nodes.state.dataset.state, 'mismatch');
  assert.equal(h.nodes.state.textContent, 'Freighter account changed');
  assert.equal(h.nodes.message.textContent, 'Freighter changed accounts. Reconnect to use the active account in Push.');
  assert.equal(h.nodes.address.textContent, OTHER_ADDRESS);
  assert.match(h.nodes.chip.textContent, /^Saved /);
  assert.equal(h.nodes.disconnect.hidden, true);
});

// 5. The user explicitly disconnects from Push
test('5. User explicitly disconnecting from Push ends active session while keeping saved address', async () => {
  const h = createHarness({
    initialConnected: true,
    responder: async (url) => {
      assert.equal(url, '/wallet/disconnect/');
      return {
        status: 200,
        body: {
          ok: true,
          connected: false,
          state: 'disconnected',
          message: 'Freighter disconnected from Push.',
          savedAddress: SAVED_ADDRESS,
        },
      };
    },
  });

  await h.submitDisconnect();
  assert.equal(h.nodes.state.dataset.state, 'disconnected');
  assert.equal(h.nodes.state.textContent, 'Freighter disconnected');
  assert.equal(h.nodes.message.textContent, 'Freighter disconnected from Push.');
  assert.equal(h.nodes.address.textContent, SAVED_ADDRESS);
  assert.match(h.nodes.chip.textContent, /^Saved /);
  assert.equal(h.nodes.disconnect.hidden, true);
  assert.equal(h.disconnectForm.hidden, true);
  assert.equal(h.statusNode.dataset.state, 'success');
  assert.equal(h.statusNode.textContent, 'Freighter disconnected from Push.');
});

// 6. Automatic wallet synchronisation must not reconnect an explicitly disconnected session
test('6. Automatic wallet synchronisation does not reconnect an explicitly disconnected session', async () => {
  let explicitlyDisconnected = false;
  const h = createHarness({
    initialConnected: true,
    responder: async (url) => {
      if (url === '/wallet/disconnect/') {
        explicitlyDisconnected = true;
        return {
          status: 200,
          body: {
            ok: true,
            connected: false,
            state: 'disconnected',
            message: 'Freighter disconnected from Push.',
            savedAddress: SAVED_ADDRESS,
          },
        };
      }
      if (url === '/wallet/sync/') {
        assert.equal(explicitlyDisconnected, true);
        return {
          status: 200,
          body: {
            ok: true,
            connected: false,
            state: 'disconnected',
            message: 'Freighter is disconnected. Your saved receiving address has not been removed.',
            savedAddress: SAVED_ADDRESS,
          },
        };
      }
      throw new Error(`Unexpected URL: ${url}`);
    },
  });

  await h.submitDisconnect();
  assert.equal(h.nodes.disconnect.hidden, true);

  h.advanceTime(6000);
  await h.triggerDOMContentLoaded();
  assert.equal(h.nodes.state.dataset.state, 'disconnected');
  assert.equal(h.nodes.state.textContent, 'Freighter disconnected');
  assert.equal(
    h.nodes.message.textContent,
    'Freighter is disconnected. Your saved receiving address has not been removed.'
  );
  assert.equal(h.nodes.disconnect.hidden, true);
  assert.match(h.nodes.chip.textContent, /^Saved /);
  assert.equal(h.reloads, 0);

  h.advanceTime(6000);
  await h.triggerFocus();
  assert.equal(h.nodes.disconnect.hidden, true);
  assert.equal(h.reloads, 0);
});

// 7. An explicit reconnect may restore the session
test('7. Explicit reconnect after disconnect restores the active testnet session', async () => {
  let sessionConnected = false;
  const h = createHarness({
    initialConnected: false,
    responder: async (url, body) => {
      if (url === '/wallet/connect/') {
        assert.equal(body.address, SAVED_ADDRESS);
        assert.equal(body.network, 'TESTNET');
        sessionConnected = true;
        // Matches core/views.py wallet_connect payload
        return {
          status: 200,
          body: {
            ok: true,
            message: 'Freighter connected on Stellar testnet.',
            address: SAVED_ADDRESS,
          },
        };
      }
      if (url === '/wallet/sync/') {
        return {
          status: 200,
          body: {
            ok: true,
            connected: sessionConnected,
            state: sessionConnected ? 'connected' : 'disconnected',
            message: sessionConnected
              ? 'Freighter is connected on Stellar testnet.'
              : 'Freighter is disconnected. Your saved receiving address has not been removed.',
            activeAddress: sessionConnected ? SAVED_ADDRESS : '',
            savedAddress: SAVED_ADDRESS,
          },
        };
      }
      throw new Error(`Unexpected URL: ${url}`);
    },
  });

  await h.triggerDOMContentLoaded();
  assert.equal(h.nodes.state.dataset.state, 'disconnected');
  assert.equal(h.nodes.disconnect.hidden, true);

  await h.clickConnect();
  assert.equal(h.statusNode.dataset.state, 'success');
  assert.equal(h.statusNode.textContent, 'Freighter connected on Stellar testnet.');
  assert.equal(h.nodes.state.dataset.state, 'connected');
  assert.equal(h.nodes.state.textContent, 'Connected to Freighter');
  assert.equal(h.nodes.address.textContent, SAVED_ADDRESS);
  assert.equal(h.nodes.disconnect.hidden, false);
  assert.equal(h.disconnectForm.hidden, false);

  h.advanceTime(6000);
  await h.triggerFocus();
  assert.equal(h.nodes.state.dataset.state, 'connected');
  assert.equal(h.nodes.disconnect.hidden, false);
  assert.equal(h.reloads, 0);
});

// 8. A matching testnet wallet shows connected exactly once without a reload loop
test('8. Matching testnet wallet shows connected exactly once without a reload loop', async () => {
  const h = createHarness({
    initialConnected: true,
    result: {
      connected: true,
      state: 'connected',
      activeAddress: SAVED_ADDRESS,
      savedAddress: SAVED_ADDRESS,
      message: 'Freighter is connected on Stellar testnet.',
    },
  });

  await h.triggerDOMContentLoaded();
  assert.equal(h.nodes.disconnect.hidden, false);
  assert.equal(h.nodes.state.dataset.state, 'connected');
  assert.equal(h.nodes.state.textContent, 'Connected to Freighter');
  assert.equal(h.nodes.message.textContent, 'Freighter is connected on Stellar testnet.');
  assert.equal(h.reloads, 0);
  assert.equal(h.requests.length, 1);

  // Subsequent focus/visibility events within 5s are throttled; after 5s they sync without reloading
  await h.triggerFocus();
  assert.equal(h.requests.length, 1);
  assert.equal(h.reloads, 0);

  h.advanceTime(6000);
  await h.triggerFocus();
  assert.equal(h.requests.length, 2);
  assert.equal(h.reloads, 0);

  h.advanceTime(6000);
  await h.triggerVisibilityChange(false);
  assert.equal(h.requests.length, 3);
  assert.equal(h.reloads, 0);
});

// 9. A changed wallet account removes signing readiness
test('9. Changed wallet account removes signing readiness and blocks payment signing', async () => {
  let activeAccount = SAVED_ADDRESS;
  let signCalled = false;
  let prepareCalled = false;

  const h = createHarness({
    initialConnected: true,
    freighterApi: {
      async getAddress() { return { address: activeAccount }; },
      async getNetwork() { return { network: 'TESTNET' }; },
      async signTransaction() {
        signCalled = true;
        return { signedTxXdr: 'SIGNED_XDR' };
      },
    },
    responder: async (url, body) => {
      if (url === '/wallet/sync/') {
        if (body.address === SAVED_ADDRESS) {
          return {
            status: 200,
            body: {
              ok: true,
              connected: true,
              state: 'connected',
              activeAddress: SAVED_ADDRESS,
              savedAddress: SAVED_ADDRESS,
              message: 'Testnet · ready to sign',
            },
          };
        }
        return {
          status: 200,
          body: {
            ok: true,
            connected: false,
            state: 'mismatch',
            activeAddress: body.address,
            savedAddress: SAVED_ADDRESS,
            message: 'Freighter changed accounts. Reconnect to use the active account in Push.',
          },
        };
      }
      if (url === '/wallet/prepare/') {
        prepareCalled = true;
        return { status: 200, body: { ok: true, source: SAVED_ADDRESS, xdr: 'UNSIGNED_XDR' } };
      }
      throw new Error(`Unexpected URL: ${url}`);
    },
  });

  await h.triggerDOMContentLoaded();
  assert.equal(h.nodes.state.dataset.state, 'connected');
  assert.equal(h.nodes.message.textContent, 'Testnet · ready to sign');
  assert.equal(h.nodes.disconnect.hidden, false);
  assert.equal(h.staffWalletStatus.textContent, `Connected · ${SAVED_ADDRESS}`);
  assert.equal(h.reloads, 0);

  // Switch active account in Freighter
  activeAccount = OTHER_ADDRESS;
  await h.submitPayment();

  assert.equal(h.nodes.state.dataset.state, 'mismatch');
  assert.equal(h.nodes.state.textContent, 'Freighter account changed');
  assert.equal(h.nodes.message.textContent, 'Freighter changed accounts. Reconnect to use the active account in Push.');
  assert.equal(h.nodes.disconnect.hidden, true);
  assert.equal(h.staffWalletStatus.textContent, 'Disconnected');
  assert.equal(h.staffConnectControl.hidden, false);
  assert.equal(h.reloads, 1);
  assert.equal(prepareCalled, false);
  assert.equal(signCalled, false);
  assert.equal(h.paymentStatusNode.dataset.state, 'error');
  assert.equal(
    h.paymentStatusNode.textContent,
    'Freighter changed accounts. Reconnect to use the active account in Push.'
  );
});

// 10. No private key or recovery phrase is requested or stored
test('10. No private key or recovery phrase is requested, transmitted, or stored', async () => {
  const leakedSecret = 'SCD777SECRETKEYNOTALLOWEDINPUSH7777777777777777777777777';
  const leakedMnemonic = 'abandon ability able about above absent absorb abstract absurd abuse access accident';
  const invokedMethods = [];

  const h = createHarness({
    initialConnected: false,
    freighterApi: {
      async isConnected() {
        invokedMethods.push('isConnected');
        return { isConnected: true, secretKey: leakedSecret };
      },
      async requestAccess() {
        invokedMethods.push('requestAccess');
        return {
          address: SAVED_ADDRESS,
          secretKey: leakedSecret,
          privateKey: leakedSecret,
          mnemonic: leakedMnemonic,
          recoveryPhrase: leakedMnemonic,
        };
      },
      async getAddress() {
        invokedMethods.push('getAddress');
        return {
          address: SAVED_ADDRESS,
          secretKey: leakedSecret,
          recoveryPhrase: leakedMnemonic,
        };
      },
      async getNetwork() {
        invokedMethods.push('getNetwork');
        return { network: 'TESTNET', seed: leakedSecret };
      },
    },
    responder: async () => ({
      status: 200,
      body: {
        ok: true,
        connected: true,
        state: 'connected',
        address: SAVED_ADDRESS,
        activeAddress: SAVED_ADDRESS,
        savedAddress: SAVED_ADDRESS,
        message: 'Freighter connected on Stellar testnet.',
      },
    }),
  });

  await h.clickConnect();
  h.advanceTime(6000);
  await h.triggerDOMContentLoaded();

  assert.deepEqual(invokedMethods, ['isConnected', 'requestAccess', 'getNetwork', 'isConnected', 'getNetwork', 'getAddress']);
  assert.equal(h.storageWrites.length, 0);
  assert.equal(h.document.cookie, '');
  assert.equal(h.requests.length, 2);

  for (const req of h.requests) {
    assert.equal(req.rawBody.includes(leakedSecret), false);
    assert.equal(req.rawBody.includes(leakedMnemonic), false);
    assert.equal('secretKey' in req.body, false);
    assert.equal('privateKey' in req.body, false);
    assert.equal('mnemonic' in req.body, false);
    assert.equal('recoveryPhrase' in req.body, false);
    assert.equal('seed' in req.body, false);
  }
});
