(function () {
  function csrfToken() {
    var match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
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
    if (response.redirected || response.status === 401 || response.status === 403 || /<html/i.test(body)) {
      throw new Error('Your Push session has expired. Refresh the page, sign in again, then reconnect Freighter.');
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
      if (!connection || !connection.isConnected) {
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
      var response = await fetch(button.dataset.walletEndpoint, {
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

  document.addEventListener('click', function (event) {
    var button = event.target.closest('[data-wallet-connect]');
    if (!button) return;
    event.preventDefault();
    connectWallet(button);
  });
}());
