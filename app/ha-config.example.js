/* Copy this file to ha-config.js (gitignored) and fill in your own values.
   ha-config.js is never committed and must never be packaged with placeholder
   values. See docs/development.md for the Home Assistant webhook setup. */
var HA_CONFIG = {
  base: 'http://<HA_LAN_IP>:8123',
  actions: {
    lightsOn: '<webhook-id>',
    lightsOff: '<webhook-id>',
    jellyfinSyncOn: '<webhook-id>',
    jellyfinSyncOff: '<webhook-id>'
  }
};
