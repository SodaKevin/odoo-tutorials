from odoo import models, fields, api
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero
from datetime import timedelta

class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Real Estate Property"
    _order = "id desc"
    _check_company_auto = True

    # ─── Active Field ──────────────────────────────────────────────────
    active = fields.Boolean(string="Active", default=True)

    # ─── Basic Fields ──────────────────────────────────────────────────
    name = fields.Char(string="Title", required=True)
    description = fields.Text(string="Description")
    postcode = fields.Char(string="Postcode")
    
    # ─── Date Field with Default ──────────────────────────────────────
    date_availability = fields.Date(
        string="Date Availability",
        default=lambda self: fields.Date.today() + timedelta(days=90),
        copy=False
    )
    
    # ─── Price Fields ──────────────────────────────────────────────────
    expected_price = fields.Float(string="Expected Price", required=True)
    selling_price = fields.Float(
        string="Selling Price",
        readonly=True,
        copy=False
    )
    
    # ─── Bedrooms with Default Value ──────────────────────────────────
    bedrooms = fields.Integer(
        string="Bedrooms",
        default=2
    )
    
    # ─── Other Fields ──────────────────────────────────────────────────
    living_area = fields.Integer(string="Living Area (sqm)")
    facades = fields.Integer(string="Facades")
    garage = fields.Boolean(string="Garage")
    garden = fields.Boolean(string="Garden")
    garden_area = fields.Integer(string="Garden Area (sqm)")
    garden_orientation = fields.Selection(
        string='Garden Orientation',
        selection=[
            ('north', 'North'),
            ('south', 'South'),
            ('east', 'East'),
            ('west', 'West')
        ]
    )

    # ─── Computed Fields ──────────────────────────────────────────────
    total_area = fields.Integer(
        string="Total Area (sqm)",
        compute="_compute_total_area",
        store=True
    )
    
    best_offer = fields.Float(
        string="Best Offer",
        compute="_compute_best_offer",
        store=True
    )

    @api.depends('living_area', 'garden_area')
    def _compute_total_area(self):
        """Compute total area as sum of living area and garden area"""
        for record in self:
            record.total_area = (record.living_area or 0) + (record.garden_area or 0)

    @api.depends('offer_ids.price')
    def _compute_best_offer(self):
        """Compute best offer as maximum of all offer prices"""
        for record in self:
            record.best_offer = max(record.offer_ids.mapped('price')) if record.offer_ids else 0.0

    # ─── Onchange Methods ──────────────────────────────────────────────
    
    @api.onchange('garden')
    def _onchange_garden(self):
        """When garden is checked, set default garden area and orientation.
           When garden is unchecked, clear garden area and orientation."""
        if self.garden:
            # Set default values when garden is enabled
            self.garden_area = 10
            self.garden_orientation = 'north'
        else:
            # Clear values when garden is disabled
            self.garden_area = 0
            self.garden_orientation = False
    
    # ─── Offer Relationship ────────────────────────────────────────────
    offer_ids = fields.One2many(
        'estate.property.offer',
        'property_id',
        string="Offers"
    )
    
    # ─── State Field ────────────────────────────────────────────────────
    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('offer_received', 'Offer Received'),
            ('offer_accepted', 'Offer Accepted'),
            ('sold', 'Sold'),
            ('canceled', 'Canceled')
        ],
        string="Status",
        default='new',
        required=True,
        copy=False,
        readonly=True
    )
    
    # ─── Relational Fields ─────────────────────────────────────────────
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        required=True,
        ondelete='restrict',
        default=lambda self: self.env.company
    )

    buyer_id = fields.Many2one(
        'res.partner',
        ondelete='set null',
        string="Buyer"
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        ondelete='set null',
        string="Invoice"
    )
    
    user_id = fields.Many2one(
        'res.users',
        string="Salesperson",
        default=lambda self: self.env.user,
        ondelete='set null'
    )

    # ─── Property Type & Tags ──────────────────────────────────────────
    property_type_id = fields.Many2one(
        'estate.property.type',
        string="Property Type"
    )
    
    tag_ids = fields.Many2many(
        'estate.property.tag',
        string="Property Tags"
    )
    
    # ─── Methods ────────────────────────────────────────────────────────
    
    def action_cancel(self):
        """Cancel the property. A sold property cannot be canceled."""
        for record in self:
            if record.state == 'sold':
                raise UserError("Cannot cancel a sold property!")
            if record.state == 'canceled':
                raise UserError("Property is already canceled!")
            record.state = 'canceled'
        return True

    def action_sold(self):
        """Mark the property as sold. A canceled property cannot be sold."""
        for record in self:
            if record.state == 'canceled':
                raise UserError("Cannot sell a canceled property!")
            if record.state == 'sold':
                raise UserError("Property is already sold!")
            record.state = 'sold'
        return True
    
    _sql_constraints = [
        (
            'check_expected_price',
            'CHECK(expected_price > 0)',
            'The expected price must be strictly positive.'
        ),
        (
            'check_selling_price',
            'CHECK(selling_price >= 0)',
            'The selling price must be positive.'
        ),
    ]

    @api.constrains('selling_price', 'expected_price')
    def _check_selling_price(self):
        for record in self:
            # Ignore unsold properties
            if float_is_zero(record.selling_price, precision_rounding=0.01):
                continue

            min_price = record.expected_price * 0.9

            if float_compare(
                record.selling_price,
                min_price,
                precision_rounding=0.01
            ) < 0:
                raise ValidationError(
                    "The selling price cannot be lower than 90% of the expected price."
                )
            
    @api.ondelete(at_uninstall=False)
    def _unlink_if_not_new_or_cancelled(self):
        for property in self:
            if property.state not in ('new', 'canceled'):
                raise UserError(
                    "Only new or cancelled properties can be deleted."
                )