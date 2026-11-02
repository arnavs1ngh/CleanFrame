set -u
printf 'CLEANFRAME_DEBLOAT_BEGIN\n'
before=$(sqlite3 /opt/dbspace/.pkgmgr_parser.db "SELECT app_disable FROM package_app_info WHERE app_id='yL49PNFmjW.service';")
printf 'BEFORE app_disable=%s\n' "$before"
pkgcmd -A -t app -n yL49PNFmjW.service --global 2>&1
printf 'PKGCMD_EXIT=%s\n' "$?"
after=$(sqlite3 /opt/dbspace/.pkgmgr_parser.db "SELECT app_disable FROM package_app_info WHERE app_id='yL49PNFmjW.service';")
printf 'AFTER app_disable=%s (should be false - the original value)\n' "$after"
onboot=$(sqlite3 /opt/dbspace/.pkgmgr_parser.db "SELECT app_onboot FROM package_app_info WHERE app_id='yL49PNFmjW.service';")
autorestart=$(sqlite3 /opt/dbspace/.pkgmgr_parser.db "SELECT app_autorestart FROM package_app_info WHERE app_id='yL49PNFmjW.service';")
printf 'AFTER app_onboot=%s app_autorestart=%s (should be unchanged: false false)\n' "$onboot" "$autorestart"
printf 'CLEANFRAME_DEBLOAT_END\n'
