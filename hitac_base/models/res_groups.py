# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.exceptions import AccessError

SYS_ADMIN_GROUP = 'hitac_base.group_sys_admin'


class ResGroups(models.Model):
    _inherit = 'res.groups'

    def _hitac_grants_sys_admin(self):
        """ True if this group, or any group it implies (recursively), is
        System Admin. """
        sys_admin_group = self.env.ref(SYS_ADMIN_GROUP, raise_if_not_found=False)
        return bool(sys_admin_group) and sys_admin_group in self.all_implied_ids

    def _hitac_forbid_indirect_promotion(self):
        for group in self:
            if group.user_ids and group._hitac_grants_sys_admin():
                self.env['ir.model.access'].call_cache_clearing_methods()
                raise AccessError(_(
                    "Only a System Admin can add users to a group that grants "
                    "System Admin access, whether directly or through an "
                    "implied group."
                ))

    @api.model_create_multi
    def create(self, vals_list):
        # A brand new group can be created with implied_ids pointing (even
        # indirectly) at System Admin and user_ids already populated in the
        # same call — bypasses any check that only looks at write().
        if self.env.su or self.env.user.has_group(SYS_ADMIN_GROUP):
            return super().create(vals_list)

        with self.env.cr.savepoint():
            records = super().create(vals_list)
            records._hitac_forbid_indirect_promotion()
        return records

    def write(self, vals):
        # implied_ids/implied_by_ids matter too: editing an already-populated
        # group's implications to reach System Admin grants it to every
        # existing member without ever touching user_ids.
        relevant = {'user_ids', 'implied_ids', 'implied_by_ids'}
        if not (relevant & vals.keys()) or self.env.su or self.env.user.has_group(SYS_ADMIN_GROUP):
            return super().write(vals)

        before_members = {group.id: set(group.user_ids.ids) for group in self}

        # Savepoint: without it, a rejected change is already applied by
        # super().write() by the time we detect and raise.
        with self.env.cr.savepoint():
            res = super().write(vals)
            for group in self:
                if not group.user_ids or not group._hitac_grants_sys_admin():
                    continue
                newly_added = set(group.user_ids.ids) - before_members[group.id]
                implication_changed = bool({'implied_ids', 'implied_by_ids'} & vals.keys())
                if newly_added or implication_changed:
                    self.env['ir.model.access'].call_cache_clearing_methods()
                    raise AccessError(_(
                        "Only a System Admin can add users to a group that "
                        "grants System Admin access, whether directly or "
                        "through an implied group."
                    ))
        return res
