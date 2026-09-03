# -*- coding: utf-8 -*-
"""19.0 gave res.users a core ``role`` field of its own.

The role of the mining app moved to ``mining_app_role`` so it stops
clobbering it; its column is renamed here, before the ORM would otherwise
create an empty one and drop the old values with it.
"""


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'res_users'
           AND column_name = 'role'
        """
    )
    if not cr.fetchone():
        return

    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'res_users'
           AND column_name = 'mining_app_role'
        """
    )
    if cr.fetchone():
        return

    cr.execute("ALTER TABLE res_users RENAME COLUMN role TO mining_app_role")
