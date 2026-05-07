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

  function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, function (c) {
      return (
        {
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          '"': '&quot;',
          "'": '&#39;',
        }[c]
      );
    });
  }

  /**
   * Non-blocking message (Bootstrap 5 toast). Variants: success, danger, warning, info.
   */
  function toast(message, variant) {
    var text = String(message != null ? message : '');
    variant = variant || 'info';
    if (typeof bootstrap === 'undefined' || !bootstrap.Toast) {
      window.alert(text);
      return;
    }
    var stack = document.getElementById('podcafeToastStack');
    if (!stack) {
      stack = document.createElement('div');
      stack.id = 'podcafeToastStack';
      stack.className = 'position-fixed top-0 end-0 p-3 podcafe-toast-stack';
      stack.style.zIndex = '1085';
      document.body.appendChild(stack);
    }
    var el = document.createElement('div');
    el.className = 'toast align-items-center border-0 shadow mt-2';
    el.setAttribute('role', 'alert');
    el.setAttribute('aria-live', 'polite');
    el.setAttribute('aria-atomic', 'true');
    var styles = {
      success: { bg: 'text-bg-success', whiteClose: true },
      danger: { bg: 'text-bg-danger', whiteClose: true },
      warning: { bg: 'text-bg-warning text-dark', whiteClose: false },
      info: { bg: 'text-bg-primary', whiteClose: true },
    };
    var st = styles[variant] || styles.info;
    el.classList.add.apply(el.classList, st.bg.split(' '));
    var closeClass = st.whiteClose ? 'btn-close btn-close-white' : 'btn-close';
    el.innerHTML =
      '<div class="d-flex w-100 align-items-center">' +
      '<div class="toast-body fw-medium mb-0 flex-grow-1 text-start pe-2">' +
      escapeHtml(text) +
      '</div>' +
      '<button type="button" class="' +
      closeClass +
      ' flex-shrink-0 ms-1 me-2" data-bs-dismiss="toast" aria-label="Close"></button>' +
      '</div>';
    stack.appendChild(el);
    var delay = variant === 'danger' ? 5600 : 4200;
    var t = new bootstrap.Toast(el, { autohide: true, delay: delay });
    el.addEventListener('hidden.bs.toast', function () {
      el.remove();
    });
    t.show();
  }

  window.PodCafe = {
    getToken: getToken,
    payloadFromToken: payloadFromToken,
    currency: currency,
    apiFetch: apiFetch,
    apiUpload: apiUpload,
    toast: toast,
  };
})(window);
