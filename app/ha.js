/* Home Assistant webhook calls. Fire-and-forget: no body, no custom headers, no live state. */
(function () {
  'use strict';
  function configured() {
    var cfg = window.HA_CONFIG, a = cfg && cfg.actions;
    return !!(cfg && typeof cfg.base === 'string' && cfg.base && a
      && typeof a.lightsOn === 'string' && a.lightsOn
      && typeof a.lightsOff === 'string' && a.lightsOff
      && typeof a.jellyfinSyncOn === 'string' && a.jellyfinSyncOn
      && typeof a.jellyfinSyncOff === 'string' && a.jellyfinSyncOff);
  }
  function bounded(done) {
    var finished = false, timer = setTimeout(function () { finish({ message: 'Couldn’t reach Home Assistant.' }); }, 4000);
    function finish(err) { if (finished) return; finished = true; clearTimeout(timer); done(err); }
    return finish;
  }
  function fire(action, done) {
    var cfg = window.HA_CONFIG, id = cfg && cfg.actions && cfg.actions[action], finish, xhr;
    if (!configured() || !id) { done({ message: 'Home Assistant is not configured.' }); return; }
    finish = bounded(done);
    try {
      xhr = new XMLHttpRequest();
      xhr.open('POST', cfg.base + '/api/webhook/' + id, true);
      xhr.timeout = 4000;
      xhr.onload = function () { finish(xhr.status >= 200 && xhr.status < 300 ? null : { message: 'Couldn’t reach Home Assistant.' }); };
      xhr.onerror = function () { finish({ message: 'Couldn’t reach Home Assistant.' }); };
      xhr.ontimeout = function () { finish({ message: 'Couldn’t reach Home Assistant.' }); };
      xhr.send();
    } catch (e) { finish({ message: 'Couldn’t reach Home Assistant.' }); }
  }
  window.HomeAssistant = { configured: configured, fire: fire };
}());
