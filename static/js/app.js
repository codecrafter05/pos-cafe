/**
 * Shared helpers for Pod Café POS web UI.
 * Uses the Maxton template assets mounted at /assets.
 */
(function (window) {
  'use strict';

  function getToken() {
    return localStorage.getItem('access_token');
  }

  function payloadFromToken(token) {
    if (!token) return null;
    try {
      var body = token.split('.')[1];
      return JSON.parse(atob(body));
    } catch (e) {
      return null;
    }
  }

  function currency(n) {
    var x = Number(n);
    if (Number.isNaN(x)) x = 0;
    return (
      'BHD ' +
      x.toLocaleString(undefined, {
        minimumFractionDigits: 3,
        maximumFractionDigits: 3,
      })
    );
  }

  async function apiFetch(path, opts) {
    opts = opts || {};
    var headers = opts.headers || {};
    var token = getToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;
    if (!headers['Content-Type'] && opts.body && typeof opts.body === 'string') {
      headers['Content-Type'] = 'application/json';
    }
    var res = await fetch(
      path,
      Object.assign({}, opts, {
        headers: headers,
        credentials: 'same-origin',
        cache: 'no-store',
      })
    );
    return res;
  }

  async function apiUpload(path, formData) {
    var headers = {};
    var token = getToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;
    return fetch(path, {
      method: 'POST',
      headers: headers,
      body: formData,
      credentials: 'same-origin',
    });
  }

  window.PodCafe = {
    getToken: getToken,
    payloadFromToken: payloadFromToken,
    currency: currency,
    apiFetch: apiFetch,
    apiUpload: apiUpload,
  };
})(window);
