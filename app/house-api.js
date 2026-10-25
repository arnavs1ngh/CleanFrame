/* house-api client. ES5, XMLHttpRequest only. Fetches GET /v1/home on a
   timer while the Home screen is visible, persists the last good response
   so boot can paint immediately (marked stale until a live fetch confirms
   it), and posts allowlisted tile actions. No optimistic state: callers
   always render whatever the server last said. */
(function () {
  'use strict';
  var STORAGE_KEY = 'cleanframe.house-api.v1';
  var DEFAULT_REFRESH_S = 60;
  var REQUEST_TIMEOUT_MS = 8000;
  var ACTION_TIMEOUT_MS = 4000;
  var BACKOFF_BASE_MS = 5000;
  var BACKOFF_CAP_MS = 5 * 60 * 1000;

  var listeners = [];
  var pollTimer = null;
  var backoffMs = 0;
  var refreshS = DEFAULT_REFRESH_S;
  var started = false;
  var homeInFlight = false;
  var actionsInFlight = {};
  var refreshWaiters = [];

  function base() { return typeof window.HOUSE_API_BASE === 'string' && window.HOUSE_API_BASE ? window.HOUSE_API_BASE : ''; }
  function configured() { return !!base(); }

  function loadCache() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      var saved = JSON.parse(raw);
      return saved && typeof saved === 'object' && saved.home ? saved : null;
    } catch (e) { return null; }
  }
  function saveCache(home, etag) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ home: home, etag: etag || '', savedAt: new Date().toISOString() })); }
    catch (e) { /* storage unavailable: keep running in-memory only */ }
  }

  function notify(envelope) {
    for (var i = 0; i < listeners.length; i++) {
      try { listeners[i](envelope); } catch (e) { /* one bad listener must not break the others */ }
    }
  }

  function scheduleNext(ms) {
    clearTimeout(pollTimer);
    pollTimer = setTimeout(poll, ms);
  }
  function poll() { if (!document.hidden) fetchHome(); }

  function fetchHome() {
    if (!configured() || homeInFlight) return;
    homeInFlight = true;
    var cached = loadCache(), finished = false, timer, xhr;
    function finish(err, result) {
      if (finished) return;
      finished = true; clearTimeout(timer); homeInFlight = false;
      if (err) onError(); else onSuccess(result);
    }
    timer = setTimeout(function () { finish({ message: 'timeout' }); }, REQUEST_TIMEOUT_MS);
    try {
      xhr = new XMLHttpRequest();
      xhr.open('GET', base() + '/v1/home', true);
      if (cached && cached.etag) xhr.setRequestHeader('If-None-Match', cached.etag);
      xhr.onload = function () {
        var data;
        if (xhr.status === 304) { finish(null, { notModified: true }); return; }
        if (xhr.status >= 200 && xhr.status < 300) {
          try { data = JSON.parse(xhr.responseText); } catch (e) { finish({ message: 'parse' }); return; }
          finish(null, { data: data, etag: xhr.getResponseHeader('ETag') || '' });
          return;
        }
        finish({ message: 'status ' + xhr.status });
      };
      xhr.onerror = function () { finish({ message: 'network' }); };
      xhr.ontimeout = function () { finish({ message: 'timeout' }); };
      xhr.send();
    } catch (e) { finish({ message: 'exception' }); }
  }

  function drainWaiters(err) {
    var waiters = refreshWaiters;
    refreshWaiters = [];
    for (var i = 0; i < waiters.length; i++) { try { waiters[i](err); } catch (e) { /* one bad waiter must not break the others */ } }
  }
  function onSuccess(result) {
    backoffMs = 0;
    var cached = loadCache(), home, etag;
    if (result.notModified) { home = cached && cached.home; etag = cached && cached.etag; }
    else { home = result.data; etag = result.etag; saveCache(home, etag); }
    if (home && home.meta && typeof home.meta.refresh_after_s === 'number' && home.meta.refresh_after_s > 0) refreshS = home.meta.refresh_after_s;
    notify({ home: home, stale: false, error: null });
    drainWaiters(null);
    scheduleNext(refreshS * 1000);
  }
  function onError() {
    backoffMs = backoffMs ? Math.min(backoffMs * 2, BACKOFF_CAP_MS) : BACKOFF_BASE_MS;
    var cached = loadCache();
    notify({ home: cached && cached.home, stale: true, error: { message: 'Couldn’t reach house-api.' } });
    drainWaiters({ message: 'Couldn’t reach house-api.' });
    scheduleNext(backoffMs);
  }

  function handleVisibility() {
    if (document.hidden) clearTimeout(pollTimer);
    else fetchHome();
  }

  function start() {
    if (started || !configured()) return;
    started = true;
    var cached = loadCache();
    if (cached && cached.home) notify({ home: cached.home, stale: true, error: null });
    document.addEventListener('visibilitychange', handleVisibility);
    if (!document.hidden) fetchHome();
  }

  /* Forces an immediate GET /v1/home ahead of the next scheduled poll, so a caller about to show
     a tile's current value (e.g. opening the Lights popup) isn't stuck with data up to
     refresh_after_s old. Piggybacks on an already-in-flight request rather than firing a second
     one. done (optional) fires once, after the next successful or failed fetch resolves. */
  function refresh(done) {
    if (!configured()) { if (done) done({ message: 'house-api is not configured.' }); return; }
    if (done) refreshWaiters.push(done);
    if (!homeInFlight) { clearTimeout(pollTimer); fetchHome(); }
  }

  /* body is optional: omit (or pass null) for a plain fire (toggle/scene/button); pass a plain
     object (e.g. { brightness: 72 }) to adjust a tile's settable fields. Always JSON. */
  function fireAction(tileId, body, done) {
    if (typeof body === 'function') { done = body; body = null; } // allow the old 2-arg call shape
    if (!configured()) { done({ message: 'house-api is not configured.' }); return; }
    if (actionsInFlight[tileId]) return; // ignore repeat presses while in flight
    actionsInFlight[tileId] = true;
    var finished = false, timer, xhr;
    function finish(err, tile) {
      if (finished) return;
      finished = true; clearTimeout(timer); delete actionsInFlight[tileId];
      done(err, tile);
    }
    timer = setTimeout(function () { finish({ message: 'Couldn’t reach house-api.' }); }, ACTION_TIMEOUT_MS);
    try {
      xhr = new XMLHttpRequest();
      xhr.open('POST', base() + '/v1/actions/' + encodeURIComponent(tileId), true);
      xhr.timeout = ACTION_TIMEOUT_MS;
      if (body) xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.onload = function () {
        var parsed;
        if (xhr.status < 200 || xhr.status >= 300) { finish({ message: 'Couldn’t reach house-api.' }); return; }
        try { parsed = JSON.parse(xhr.responseText); } catch (e) { finish({ message: 'Couldn’t reach house-api.' }); return; }
        if (!parsed || parsed.ok !== true) { finish({ message: 'Action failed.' }, parsed && parsed.tile); return; }
        finish(null, parsed.tile);
      };
      xhr.onerror = function () { finish({ message: 'Couldn’t reach house-api.' }); };
      xhr.ontimeout = function () { finish({ message: 'Couldn’t reach house-api.' }); };
      xhr.send(body ? JSON.stringify(body) : null);
    } catch (e) { finish({ message: 'Couldn’t reach house-api.' }); }
  }

  window.HouseAPI = {
    configured: configured,
    start: start,
    subscribe: function (fn) { listeners.push(fn); },
    refresh: refresh,
    fireAction: fireAction
  };
}());
