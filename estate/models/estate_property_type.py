from odoo import models, fields

class EstatePropertyType(models.Model):
    _name = "estate.property.type"
    _description = "Property Type"
    
    name = fields.Char(string="Name", required=True)
    _order = "sequence, name"

    # ─── Relational Fields ─────────────────────────────────────────
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        required=True,
        ondelete='restrict',
        default=lambda self: self.env.company
    )

    # NEW: Buyer (res.partner)
    buyer_id = fields.Many2one(
        'res.partner',
        string="Buyer",
        ondelete='set null',
        copy=False  # Don't copy when duplicating
    )

    # NEW: Salesperson (res.users) - Default to current user
    user_id = fields.Many2one(
        'res.users',
        string="Salesperson",
        default=lambda self: self.env.user,
        ondelete='set null'
    )

    # NEW: Property Type (estate.property.type) - ALREADY EXISTS in your code!
    # You already have this field, just make sure it's there:
    property_type_id = fields.Many2one(
        'estate.property.type',
        string="Property Type"
    )

    tag_ids = fields.Many2many(
        'estate.property.tag',
        string="Property Tags"
    )

    property_ids = fields.One2many(
        'estate.property',
        'property_type_id',
        string='Properties'
    )

    sequence = fields.Integer(
        string="Sequence",
        default=10
    )

    _sql_constraints = [
        (
            'unique_property_type_name',
            'UNIQUE(name)',
            'Property type name must be unique.'
        ),
    ]
