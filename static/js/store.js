/**
 * Customer online store — cart in sessionStorage (key: podcafe_store_cart_v1)
 */
(function (window) {
  'use strict';

  var CART_KEY = 'podcafe_store_cart_v2_en';

  function getCart() {
    try {
      var raw = sessionStorage.getItem(CART_KEY);
      var j = raw ? JSON.parse(raw) : [];
      return Array.isArray(j) ? j : [];
    } catch (e) {
      return [];
    }
  }

  function setCart(lines) {
    sessionStorage.setItem(CART_KEY, JSON.stringify(lines));
    updateNavBadge();
  }

  function cartLineTotal(line) {
    var base = Number(line.base_price) || 0;
    var extra = 0;
    (line.modifiers || []).forEach(function (m) {
      extra += Number(m.extra_price) || 0;
    });
    return (base + extra) * (Number(line.quantity) || 1);
  }

  function cartTotal(lines) {
    return lines.reduce(function (s, l) {
      return s + cartLineTotal(l);
    }, 0);
  }

  function updateNavBadge() {
    var el = document.getElementById('navCartCount');
    if (!el) return;
    var n = getCart().reduce(function (s, l) {
      return s + (Number(l.quantity) || 1);
    }, 0);
    el.textContent = String(n);
  }

  function currencyBhd(n) {
    var x = Number(n);
    if (isNaN(x)) x = 0;
    return (
      'BHD ' +
      x.toLocaleString('en-BH', {
        style: 'decimal',
        minimumFractionDigits: 3,
        maximumFractionDigits: 3,
      })
    );
  }

  window.PodCafeStore = {
    CART_KEY: CART_KEY,
    getCart: getCart,
    setCart: setCart,
    cartLineTotal: cartLineTotal,
    cartTotal: cartTotal,
    updateNavBadge: updateNavBadge,
    currencyBhd: currencyBhd,
  };

  document.addEventListener('DOMContentLoaded', updateNavBadge);
})(window);
