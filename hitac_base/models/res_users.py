# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

SYS_ADMIN_GROUP = 'hitac_base.group_sys_admin'

HITAC_DEPARTMENTS = [
    ('sales', 'Sales'),
    ('marketing', 'Marketing'),
    ('production', 'Production'),
    ('logistics', 'Logistics'),
    ('supply', 'Supply'),
    ('external', 'External'),
]


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Same related-field pattern base already uses for name/email/phone
    # (res_users.py) to surface partner fields on the user form. Without
    # this, creating a user from Settings has no way to set the partner's
    # required hitac_type, and saving fails.
    hitac_type = fields.Selection(related='partner_id.hitac_type', inherited=True, readonly=False)

    # Optional — which Hitac department a user belongs to, purely for
    # organizing/filtering the Users list. Not tied to their access
    # groups; a user's actual permissions still come from group_ids.
    hitac_department = fields.Selection(HITAC_DEPARTMENTS, string='Department')

    def _hitac_clear_group_caches(self):
        # has_group()/_get_group_ids() are @tools.ormcache'd at the
        # registry level, independent of the SQL transaction. A savepoint
        # rollback undoes the SQL, but if our own has_group() checks just
        # refreshed this cache to the (about to be rejected) value, it
        # stays stale afterwards unless explicitly cleared here.
        self.env['ir.model.access'].call_cache_clearing_methods()

    @api.model_create_multi
    def create(self, vals_list):
        # Skipped under sudo()/superuser: internal Odoo mechanisms (e.g.
        # mail's notification-type inverse) do their own group_ids writes
        # as a side effect of plain user creation, run in that context —
        # not a human deliberately assigning System Admin.
        if self.env.su:
            return super().create(vals_list)

        with self.env.cr.savepoint():
            records = super().create(vals_list)
            if (
                any(record.has_group(SYS_ADMIN_GROUP) for record in records)
                and not self.env.user.has_group(SYS_ADMIN_GROUP)
            ):
                self._hitac_clear_group_caches()
                raise UserError(_('Only a System Admin can promote another user to System Admin.'))
        return records

    def write(self, vals):
        if 'group_ids' not in vals or self.env.su:
            return super().write(vals)

        actor_is_sys_admin = self.env.user.has_group(SYS_ADMIN_GROUP)
        was_sys_admin = {user.id: user.has_group(SYS_ADMIN_GROUP) for user in self}

        # Rule 1: a non-System-Admin can't touch the groups of a user who
        # already has System Admin at all. A System Admin actor is exempt —
        # they can do anything, including editing another System Admin's
        # groups. Checked before the write goes through.
        if not actor_is_sys_admin and any(was_sys_admin.values()):
            raise UserError(_("You can't update a System Admin's groups."))

        # Savepoint: without it, a rejected promotion below has already
        # been applied by super().write() by the time we detect and raise
        # — fine for a single web request (the whole transaction rolls
        # back on the error), but not if anything else runs more ORM calls
        # in the same transaction afterwards (verified this actually
        # happens: a rejected promotion's leftover state incorrectly
        # blocked a legitimate one moments later in the same transaction).
        with self.env.cr.savepoint():
            res = super().write(vals)
            # Rule 2: promoting someone who wasn't already a System Admin
            # requires the acting user to already be one themselves.
            if not actor_is_sys_admin:
                newly_granted = any(
                    user.has_group(SYS_ADMIN_GROUP) and not was_sys_admin[user.id]
                    for user in self
                )
                if newly_granted:
                    self._hitac_clear_group_caches()
                    raise UserError(_('Only a System Admin can promote another user to System Admin.'))
        return res
