set -u
printf 'CLEANFRAME_DEBLOAT_BEGIN\n'
sqlite3 /opt/dbspace/.pkgmgr_parser.db -header -line "SELECT app_id, app_disable, app_onboot, app_autorestart FROM package_app_info WHERE app_id='yL49PNFmjW.service';"
printf 'CLEANFRAME_DEBLOAT_END\n'
