def post_init_hook(env):
    """Auto-assign Odoo system admins to the hotel admin group on module install."""
    cr = env.cr
    cr.execute("""
        INSERT INTO res_groups_users_rel (gid, uid)
        SELECT g_hotel.id, g_sys.uid
        FROM res_groups g_hotel
        CROSS JOIN (
            SELECT uid FROM res_groups_users_rel rgu
            JOIN res_groups g ON g.id = rgu.gid
            JOIN ir_model_data imd ON imd.res_id = g.id
                AND imd.model = 'res.groups'
                AND imd.module = 'base'
                AND imd.name = 'group_system'
        ) g_sys
        JOIN ir_model_data imd2 ON imd2.res_id = g_hotel.id
            AND imd2.model = 'res.groups'
            AND imd2.module = 'leapai_hotel_management'
            AND imd2.name = 'group_hotel_admin'
        ON CONFLICT DO NOTHING
    """)
