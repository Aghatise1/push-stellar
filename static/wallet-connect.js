(function () {
  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    var match = document.cookie.match(/(?:^|; )(?:__Host-push_csrf|push_csrftoken|csrftoken)=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function statusNodes() {
    var nodes = Array.prototype.slice.call(document.querySelectorAll('[data-wallet-status]'));
    var toast = document.querySelector('.wallet-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.className = 'wallet-toast';
      toast.setAttribute('role', 'status');
      toast.setAttribute('aria-live', 'polite');
      toast.hidden = true;
      document.body.appendChild(toast);
    }
    if (nodes.indexOf(toast) === -1) nodes.push(toast);
    return nodes;
  }

  function showStatus(message, state) {
    statusNodes().forEach(function (node) {
      node.textContent = message;
      node.dataset.state = state || 'working';
      node.hidden = false;
    });
  }

  function errorMessage(error, fallback) {
    if (!error) return fallback;
    if (typeof error === 'string') return error;
    return error.message || error.code || fallback;
  }

  function walletShell() {
    return document.querySelector('[data-wallet-shell]');
  }

  function shortAddress(address) {
    return address ? address.slice(0, 6) + '…' + address.slice(-4) : '';
  }

  function renderWalletState(result) {
    var shell = walletShell();
    if (!shell || !result) return;
    var chip = shell.querySelector('[data-wallet-chip]');
    var state = shell.querySelector('[data-wallet-state]');
    var address = shell.querySelector('[data-wallet-address]');
    var message = shell.querySelector('[data-wallet-message]');
    var disconnect = shell.querySelector('[data-wallet-disconnect]');
    var active = result.activeAddress || '';
    var saved = result.savedAddress || shell.dataset.savedAddress || '';
    var connected = Boolean(result.connected && active);
    if (chip) chip.textContent = connected ? shortAddress(active) : (saved ? 'Saved ' + shortAddress(saved) : 'Connect wallet');
    if (state) {
      state.dataset.state = connected ? 'connected' : (result.state || 'disconnected');
      state.textContent = connected ? 'Connected to Freighter' : ({
        mismatch: 'Freighter account changed',
        wrong_network: 'Wrong Stellar network',
        needs_connection: 'Approval required'
      }[result.state] || 'Freighter disconnected');
    }
    if (address) address.textContent = active || saved || 'No saved receiving address';
    if (message) message.textContent = result.message || (connected ? 'Testnet · ready to sign' : 'Reconnect Freighter to send.');
    if (disconnect) disconnect.hidden = !connected;
  }

  async function apiResult(response) {
    var contentType = response.headers.get('content-type') || '';
    var body = await response.text();
    if (contentType.indexOf('application/json') !== -1) {
      try {
        return JSON.parse(body);
      } catch (_error) {
        throw new Error('Push returned an invalid wallet response. Refresh the page and try again.');
      }
    }
    if (response.redirected || response.status === 401) {
      throw new Error('Your Push session has expired. Refresh the page, sign in again, then reconnect Freighter.');
    }
    if (response.status === 403) {
      throw new Error('Push could not verify this request. Reload the page once, then reconnect Freighter.');
    }
    if (/<html/i.test(body)) {
      throw new Error('The wallet service returned an unexpected page. Reload Push and try again.');
    }
    throw new Error('The wallet service is temporarily unavailable. Refresh the page and try again.');
  }

  async function connectWallet(button) {
    var buttons = document.querySelectorAll('[data-wallet-connect]');
    buttons.forEach(function (item) {
      item.disabled = true;
      item.setAttribute('aria-busy', 'true');
    });
    showStatus('Looking for Freighter in this browser…');

    try {
      if (!window.freighterApi) {
        throw new Error('Freighter could not load. Open Push in Chrome or Edge with Freighter installed, then try again.');
      }

      var connection = await window.freighterApi.isConnected();
      var connected = typeof connection === 'boolean' ? connection : Boolean(connection && connection.isConnected);
      if (!connected) {
        throw new Error('Freighter is not available in this browser. Open Push in Chrome or Edge with the extension installed, or enter a public testnet address manually.');
      }

      var addressResult;
      if (typeof window.freighterApi.requestAccess === 'function') {
        addressResult = await window.freighterApi.requestAccess();
        if (addressResult && addressResult.error) {
          throw new Error(errorMessage(addressResult.error, 'Wallet access was not approved in Freighter.'));
        }
      } else {
        var permission = await window.freighterApi.setAllowed();
        if (!permission || !permission.isAllowed) {
          throw new Error('Wallet access was not approved in Freighter.');
        }
        addressResult = await window.freighterApi.getAddress();
      }

      var networkResult = await window.freighterApi.getNetwork();
      if (!addressResult || addressResult.error || !addressResult.address) {
        throw new Error('Freighter did not return a public address. Unlock it and try again.');
      }
      if (!networkResult || networkResult.error || !networkResult.network) {
        throw new Error('Freighter did not return its current network.');
      }

      showStatus('Saving your testnet public address…');
      var shell = walletShell();
      var endpoint = button.dataset.walletEndpoint || (shell && shell.dataset.walletConnectEndpoint);
      if (!endpoint) throw new Error('The wallet connection endpoint is unavailable. Refresh Push and try again.');
      var response = await fetch(endpoint, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken()},
        body: JSON.stringify({address: addressResult.address, network: networkResult.network})
      });
      var result = await apiResult(response);
      if (!response.ok || !result.ok) {
        throw new Error(result.message || 'Push could not save this wallet.');
      }

      showStatus(result.message, 'success');
      window.setTimeout(function () { window.location.reload(); }, 700);
    } catch (error) {
      showStatus(errorMessage(error, 'Wallet connection failed. Try again from Freighter.'), 'error');
    } finally {
      buttons.forEach(function (item) {
        item.disabled = false;
        item.removeAttribute('aria-busy');
      });
    }
  }

  async function syncWallet(options) {
    var shell = walletShell();
    if (!shell || !shell.dataset.walletSyncEndpoint) return null;
    var payload = {connected: false};
    try {
      if (window.freighterApi) {
        var connection = await window.freighterApi.isConnected();
        var connected = typeof connection === 'boolean' ? connection : Boolean(connection && connection.isConnected);
        if (connected) {
          var network = await window.freighterApi.getNetwork();
          var address = await window.freighterApi.getAddress();
          if (network && !network.error && address && !address.error && address.address) {
            payload = {connected: true, network: network.network, address: address.address};
          }
        }
      }
      var result = await postJson(shell.dataset.walletSyncEndpoint, payload);
      renderWalletState(result);
      if (shell.dataset.initialConnected !== String(Boolean(result.connected))) {
        shell.dataset.initialConnected = String(Boolean(result.connected));
        window.location.reload();
      }
      return result;
    } catch (error) {
      if (!(options && options.quiet)) showStatus(errorMessage(error, 'Push could not refresh the Freighter connection.'), 'error');
      return null;
    }
  }

  async function disconnectWallet(form) {
    var shell = walletShell();
    var endpoint = form.action || (shell && shell.dataset.walletDisconnectEndpoint);
    try {
      var result = await postJson(endpoint, {});
      renderWalletState(result);
      showStatus(result.message, 'success');
      window.setTimeout(function () { window.location.reload(); }, 500);
    } catch (error) {
      showStatus(errorMessage(error, 'Push could not disconnect this wallet session.'), 'error');
    }
  }

  function paymentStatus(form, message, state, explorerUrl) {
    var node = form.parentElement.querySelector('[data-payment-status]');
    if (!node) return;
    node.textContent = message;
    node.dataset.state = state || 'working';
    node.hidden = false;
    if (explorerUrl) {
      var link = document.createElement('a');
      link.href = explorerUrl;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = ' View confirmed transaction ↗';
      node.appendChild(link);
    }
  }

  async function postJson(url, payload) {
    var response = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken()},
      body: JSON.stringify(payload)
    });
    var result = await apiResult(response);
    if (!response.ok || !result.ok) throw new Error(result.message || 'The Stellar payment could not be completed.');
    return result;
  }

  async function activeFreighterAccount() {
    if (!window.freighterApi) {
      throw new Error('Freighter could not load. Open Push in Chrome or Edge with Freighter installed.');
    }
    var connection = await window.freighterApi.isConnected();
    var connected = typeof connection === 'boolean' ? connection : Boolean(connection && connection.isConnected);
    if (!connected) {
      throw new Error('Freighter is not available in this browser. Unlock the extension and try again.');
    }
    var network = await window.freighterApi.getNetwork();
    if (!network || network.error || network.network !== 'TESTNET') {
      throw new Error('Switch Freighter to Stellar testnet before sending.');
    }
    var address = await window.freighterApi.getAddress();
    if (!address || address.error || !address.address) {
      throw new Error('Freighter did not return its active public address.');
    }
    var synced = await syncWallet({quiet: true});
    if (!synced || !synced.connected || synced.activeAddress !== address.address) {
      throw new Error((synced && synced.message) || 'Reconnect the active Freighter account before sending.');
    }
    return address.address;
  }

  async function sendPayment(form) {
    var submit = form.querySelector('button[type="submit"]');
    var submitLabel = submit ? submit.textContent : '';
    if (submit) {
      submit.disabled = true;
      submit.setAttribute('aria-busy', 'true');
    }
    try {
      paymentStatus(form, 'Checking Freighter and preparing the exact testnet transaction…');
      var activeAddress = await activeFreighterAccount();
      var payload = {};
      new FormData(form).forEach(function (value, key) {
        if (key !== 'csrfmiddlewaretoken') payload[key] = value;
      });
      if (form.dataset.assignment) payload.assignment = form.dataset.assignment;
      var prepared = await postJson(form.dataset.prepareEndpoint, payload);
      if (activeAddress !== prepared.source) {
        throw new Error('Freighter is using a different account from the one connected to Push. Switch accounts or reconnect the wallet.');
      }
      paymentStatus(form, 'Review the recipient, asset, amount and memo in Freighter. Nothing moves until you approve.');
      var signed = await window.freighterApi.signTransaction(prepared.xdr, {
        networkPassphrase: prepared.networkPassphrase,
        address: prepared.source,
        accountToSign: prepared.source
      });
      if (!signed || signed.error || !signed.signedTxXdr) {
        throw new Error(errorMessage(signed && signed.error, 'The transaction was not approved in Freighter.'));
      }
      paymentStatus(form, 'Signature received. Submitting to Stellar testnet…');
      var completed = await postJson(form.dataset.submitEndpoint, {
        token: prepared.token,
        signedXdr: signed.signedTxXdr
      });
      paymentStatus(form, completed.message, 'success', completed.explorerUrl);
      if (form.dataset.assignment && completed.redirectUrl) {
        window.setTimeout(function () { window.location.assign(completed.redirectUrl); }, 1400);
      }
    } catch (error) {
      paymentStatus(form, errorMessage(error, 'The Stellar payment failed. No transaction was recorded.'), 'error');
    } finally {
      if (submit) {
        submit.disabled = false;
        submit.removeAttribute('aria-busy');
        submit.textContent = submitLabel;
      }
    }
  }

  document.addEventListener('click', function (event) {
    var button = event.target.closest('[data-wallet-connect]');
    if (!button) return;
    event.preventDefault();
    connectWallet(button);
  });

  document.addEventListener('submit', function (event) {
    var disconnectForm = event.target.closest('[data-wallet-disconnect]');
    if (disconnectForm) {
      event.preventDefault();
      disconnectWallet(disconnectForm);
      return;
    }
    var form = event.target.closest('[data-stellar-payment]');
    if (!form) return;
    event.preventDefault();
    sendPayment(form);
  });

  var syncPending = false;
  var lastSyncAt = 0;
  function refreshConnection() {
    if (syncPending || !walletShell() || Date.now() - lastSyncAt < 5000) return;
    syncPending = true;
    lastSyncAt = Date.now();
    syncWallet({quiet: true}).finally(function () { syncPending = false; });
  }
  document.addEventListener('DOMContentLoaded', refreshConnection);
  window.addEventListener('focus', refreshConnection);
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) refreshConnection();
  });
}());
