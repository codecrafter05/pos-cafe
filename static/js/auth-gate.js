/**
 * Early auth gate for admin HTML pages.
 * JWT lives in localStorage, so the server cannot redirect these routes;
 * this script must run in <head> before the page shell is painted.
 */
(function (window) {
  'use strict';

  var TOKEN_KEY = 'access_token';

  function getToken() {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch (e) {
      return null;
    }
  }

  function payloadFromToken(token) {
    if (!token) return null;
    try {
      var body = token.split('.')[1];
      if (!body) return null;
      var pad = body.replace(/-/g, '+').replace(/_/g, '/');
      while (pad.length % 4) pad += '=';
      return JSON.parse(atob(pad));
    } catch (e) {
      return null;
    }
  }

  function isAccessTokenValid(token) {
    if (token === undefined) token = getToken();
    var p = payloadFromToken(token);
    if (!p || !p.sub) return false;
    if (typeof p.exp === 'number' && Date.now() / 1000 >= p.exp) return false;
    return true;
  }

  function discardInvalidToken() {
    var token = getToken();
    if (token && !isAccessTokenValid(token)) {
      try {
        localStorage.removeItem(TOKEN_KEY);
      } catch (e) { /* private mode */ }
    }
  }

  function isSafeNext(path) {
    if (!path || typeof path !== 'string') return false;
    if (path.charAt(0) !== '/') return false;
    if (path.indexOf('//') === 0) return false;
    if (path.indexOf('\\') !== -1) return false;
    if (path.indexOf('://') !== -1) return false;
    if (path === '/login' || path.indexOf('/login?') === 0 || path.indexOf('/login#') === 0) {
      return false;
    }
    if (path.indexOf('/store') === 0) return false;
    if (path.length > 400) return false;
    return true;
  }

  function currentPath() {
    return location.pathname + location.search;
  }

  function loginUrl(next) {
    next = next == null ? currentPath() : next;
    if (!isSafeNext(next) || next === '/') return '/login';
    return '/login?next=' + encodeURIComponent(next);
  }

  function defaultAfterLogin(role) {
    return role === 'cashier' ? '/pos' : '/dashboard';
  }

  function destinationAfterLogin(role) {
    var params = new URLSearchParams(location.search);
    var next = params.get('next');
    if (isSafeNext(next)) {
      if (role === 'cashier' && (next === '/dashboard' || next.indexOf('/dashboard?') === 0)) {
        return '/pos';
      }
      return next;
    }
    return defaultAfterLogin(role);
  }

  function redirectToLogin(next) {
    if (window.__PODCAFE_REDIRECTING__) return;
    window.__PODCAFE_REDIRECTING__ = true;
    discardInvalidToken();
    try {
      document.documentElement.style.visibility = 'hidden';
    } catch (e) { /* ignore */ }
    location.replace(loginUrl(next));
  }

  function gateProtectedPage() {
    discardInvalidToken();
    if (!isAccessTokenValid()) {
      redirectToLogin();
    }
  }

  window.PodCafeAuth = {
    getToken: getToken,
    payloadFromToken: payloadFromToken,
    isAccessTokenValid: isAccessTokenValid,
    discardInvalidToken: discardInvalidToken,
    isSafeNext: isSafeNext,
    loginUrl: loginUrl,
    destinationAfterLogin: destinationAfterLogin,
    redirectToLogin: redirectToLogin,
    gateProtectedPage: gateProtectedPage,
  };

  var script = document.currentScript;
  if (script && script.getAttribute('data-podcafe-gate') === 'protected') {
    gateProtectedPage();
  }
})(window);
