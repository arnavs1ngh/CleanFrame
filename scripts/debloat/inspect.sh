set -u
printf 'CLEANFRAME_DEBLOAT_BEGIN\n'
id
printf '\nPKGCMD\n'
which pkgcmd 2>/dev/null || echo "not found"
printf '\nSQLITE3\n'
which sqlite3 2>/dev/null || echo "not found"
printf '\nPKGMGR_PARSER_DB\n'
ls -l /opt/dbspace/.pkgmgr_parser.db 2>/dev/null || find /opt -maxdepth 3 -iname "*pkgmgr_parser*" 2>/dev/null
printf '\nVCONFTOOL\n'
which vconftool 2>/dev/null || echo "not found"
printf '\nDISABLE_MECHANISM (proven 2026-11-02 against yL49PNFmjW.service / PromotionService)\n'
printf 'pkgcmd -D -t app -n <app_id> --global   # deactivate; writes package_app_info.app_disable=true\n'
printf 'pkgcmd -A -t app -n <app_id> --global   # activate;   writes package_app_info.app_disable=false\n'
printf 'Verify: sqlite3 /opt/dbspace/.pkgmgr_parser.db "SELECT app_disable FROM package_app_info WHERE app_id=%s;"\n' "'<app_id>'"
printf 'Full cycle (query, deactivate, verify, reactivate, verify) round-tripped cleanly: app_disable false->true->false, app_onboot/app_autorestart untouched throughout.\n'
printf 'CLEANFRAME_DEBLOAT_END\n'
