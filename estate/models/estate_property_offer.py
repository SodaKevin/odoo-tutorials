from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta

class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Real Estate Property Offer"
    _order = "price desc"

    # ─── Basic Fields ──────────────────────────────────────────────
    price = fields.Float(string="Price", required=True)
    
    status = fields.Selection(
        selection=[
            ('accepted', 'Accepted'),
            ('refused', 'Refused'),
        ],
        string="Status",
        copy=False
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string="Partner",
        required=True
    )
    
    property_id = fields.Many2one(
        'estate.property',
        string="Property",
        required=True,
        ondelete='cascade'
    )
    
    # ─── Offer Date (use this instead of create_date) ──────────────
    offer_date = fields.Date(
        string="Offer Date",
        default=fields.Date.today,
        required=True,
        help="Date when the offer was created"
    )
    
    # ─── Validity Fields ────────────────────────────────────────────
    validity = fields.Integer(
        string="Validity (days)",
        default=7,
        help="Number of days the offer is valid"
    )
    
    date_deadline = fields.Date(
        string="Deadline",
        compute="_compute_date_deadline",
        inverse="_inverse_date_deadline",
        store=True,
        help="Date when the offer expires"
    )
    
    # ─── Computed Methods ───────────────────────────────────────────
    
    @api.depends('offer_date', 'validity')
    def _compute_date_deadline(self):
        """Compute deadline from offer_date + validity days"""
        for record in self:
            if record.offer_date and record.validity:
                record.date_deadline = record.offer_date + timedelta(days=record.validity)
            else:
                # Fallback: use today's date if offer_date is not set
                record.date_deadline = fields.Date.today() + timedelta(days=record.validity or 7)
    
    def _inverse_date_deadline(self):
        """Inverse function: when user sets date_deadline, update validity"""
        for record in self:
            if record.date_deadline and record.offer_date:
                delta = (record.date_deadline - record.offer_date).days
                record.validity = delta if delta > 0 else 1
            elif record.date_deadline and not record.offer_date:
                # If offer_date is not set, use today
                record.offer_date = fields.Date.today()
                delta = (record.date_deadline - record.offer_date).days
                record.validity = delta if delta > 0 else 1
    
    # ─── Constraints ─────────────────────────────────────────────────
    
    @api.constrains('price')
    def _check_price_positive(self):
        for record in self:
            if record.price < 0:
                raise ValidationError("Offer price cannot be negative!")
    
    @api.constrains('validity')
    def _check_validity_positive(self):
        for record in self:
            if record.validity <= 0:
                raise ValidationError("Validity must be at least 1 day!")
    
    # ─── Business Methods ───────────────────────────────────────────
    
    def action_accept(self):
        """Accept the offer"""
        self.ensure_one()
        self.status = 'accepted'
        self.property_id.state = 'offer_accepted'
        self.property_id.selling_price = self.price
        self.property_id.buyer_id = self.partner_id
    
    def action_refuse(self):
        """Refuse the offer"""
        self.ensure_one()
        self.status = 'refused'

    # ─── Action Methods ───────────────────────────────────────────────

    def action_accept(self):
        """Accept the offer and update the property"""
        for record in self:
            # Check if there's already an accepted offer for this property
            if record.property_id.offer_ids.filtered(
                lambda o: o.status == 'accepted' and o.id != record.id
            ):
                raise UserError("Another offer has already been accepted for this property!")
            
            # Check if property is already sold or canceled
            if record.property_id.state in ['sold', 'canceled']:
                raise UserError(f"Cannot accept offer on a {record.property_id.state} property!")
            
            # Update offer status
            record.status = 'accepted'
            
            # Update property
            property_record = record.property_id
            property_record.selling_price = record.price
            property_record.buyer_id = record.partner_id
            property_record.state = 'offer_accepted'
            
            # Refuse all other offers for this property
            other_offers = property_record.offer_ids.filtered(
                lambda o: o.id != record.id and o.status != 'refused'
            )
            other_offers.action_refuse()
            
        return True

    def action_refuse(self):
        """Refuse the offer"""
        for record in self:
            if record.status == 'accepted':
                raise UserError("Cannot refuse an already accepted offer!")
            record.status = 'refused'
        return True
    
    _sql_constraints = [
        (
            'check_offer_price',
            'CHECK(price > 0)',
            'The offer price must be strictly positive.'
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:

            property_record = self.env['estate.property'].browse(
                vals['property_id']
            )

            if property_record.offer_ids:
                highest_offer = max(
                    property_record.offer_ids.mapped('price')
                )

                if vals['price'] <= highest_offer:
                    raise UserError(
                        "Offer must be higher than existing offers."
                    )

        offers = super().create(vals_list)

        for offer in offers:
            offer.property_id.state = 'offer_received'

        return offers