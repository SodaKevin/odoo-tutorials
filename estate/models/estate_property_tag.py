from odoo import models, fields, api
from odoo.exceptions import ValidationError

class EstatePropertyTag(models.Model):
    _name = "estate.property.tag"
    _description = "Property Tag"
    _order = "name"  # ← This should be a class attribute, not a field

    # ─── Basic Fields ──────────────────────────────────────────────
    name = fields.Char(string="Name", required=True)
    
    # ─── Color Field for Badges ──────────────────────────────────
    color = fields.Integer(
        string="Color Index",
        default=0,
        help="Color index for the tag badge (0-11)"
    )
    
    description = fields.Text(string="Description")
    
    # ─── Relational Fields ──────────────────────────────────────
    property_ids = fields.Many2many(
        'estate.property',
        'estate_property_tag_rel',  # Explicit relation table name
        'tag_id',                   # Column for this model
        'property_id',              # Column for estate.property
        string="Properties"
    )
    
    # ─── Computed Fields ────────────────────────────────────────
    property_count = fields.Integer(
        string="Property Count",
        compute="_compute_property_count",
        store=False
    )
    
    @api.depends('property_ids')
    def _compute_property_count(self):
        """Compute the number of properties with this tag"""
        for record in self:
            record.property_count = len(record.property_ids)
    
    # ─── Constraints ────────────────────────────────────────────
    @api.constrains('name')
    def _check_name_unique(self):
        """Ensure tag names are unique"""
        for record in self:
            if self.search_count([
                ('name', '=', record.name),
                ('id', '!=', record.id)
            ]) > 0:
                raise ValidationError(f"Tag '{record.name}' already exists!")
    
    # ─── Business Methods ──────────────────────────────────────
    def action_view_properties(self):
        """Action to view all properties with this tag"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Properties: {self.name}',
            'res_model': 'estate.property',
            'domain': [('tag_ids', 'in', self.id)],
            'view_mode': 'tree,form',
            'context': {'default_tag_ids': [(4, self.id)]},
        }
    
    _sql_constraints = [
        (
            'unique_tag_name',
            'UNIQUE(name)',
            'Tag name must be unique.'
        ),
    ]