from odoo import models, fields, api
from odoo.exceptions import UserError


class HotelTransportRequest(models.Model):
    _name = 'hotel.transport.request'
    _description = 'Hotel Transport Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Request Reference',
        readonly=True,
        default='New',
        copy=False,
        tracking=True,
    )
    booking_id = fields.Many2one('hotel.booking', string='Booking', ondelete='restrict')
    folio_id = fields.Many2one('hotel.folio', string='Folio', ondelete='restrict')
    guest_name = fields.Char(string='Guest Name')
    phone = fields.Char(string='Phone')
    trip_type = fields.Selection(
        selection=[
            ('pickup', 'Pickup'),
            ('drop', 'Drop'),
            ('round', 'Round Trip'),
        ],
        string='Trip Type',
        required=True,
    )
    pickup_location_id = fields.Many2one('hotel.transport.location', string='Pickup Location', ondelete='restrict')
    drop_location_id = fields.Many2one('hotel.transport.location', string='Drop Location', ondelete='restrict')
    pickup_datetime = fields.Datetime(string='Pickup Date & Time', required=True)
    vehicle_type = fields.Selection(
        selection=[
            ('car', 'Car'),
            ('van', 'Van'),
            ('bus', 'Bus'),
            ('luxury', 'Luxury'),
        ],
        string='Vehicle Type',
    )
    driver_name = fields.Char(string='Driver Name')
    driver_phone = fields.Char(string='Driver Phone')
    distance_km = fields.Float(
        string='Distance (KM)',
        digits=(16, 2),
        compute='_compute_distance_km',
        store=True,
    )
    charge = fields.Float(
        string='Charge',
        digits=(16, 2),
        compute='_compute_charge',
        store=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        tracking=True,
    )
    notes = fields.Text(string='Notes')

    @api.depends('pickup_location_id', 'drop_location_id', 'trip_type')
    def _compute_distance_km(self):
        for rec in self:
            pickup_km = rec.pickup_location_id.distance_km if rec.pickup_location_id else 0.0
            drop_km = rec.drop_location_id.distance_km if rec.drop_location_id else 0.0
            if rec.trip_type == 'round':
                rec.distance_km = pickup_km + drop_km
            elif rec.trip_type == 'pickup':
                rec.distance_km = pickup_km
            else:
                rec.distance_km = drop_km

    @api.depends('distance_km', 'pickup_location_id', 'drop_location_id', 'trip_type')
    def _compute_charge(self):
        for rec in self:
            price_per_km = 0.0
            if rec.pickup_location_id and rec.pickup_location_id.price_per_km:
                price_per_km = rec.pickup_location_id.price_per_km
            elif rec.drop_location_id and rec.drop_location_id.price_per_km:
                price_per_km = rec.drop_location_id.price_per_km
            rec.charge = (rec.distance_km or 0.0) * price_per_km

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.transport.request') or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only draft requests can be confirmed.')
            rec.state = 'confirmed'
        return True

    def action_start(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError('Only confirmed requests can be started.')
            rec.state = 'in_progress'
        return True

    def action_complete(self):
        for rec in self:
            if rec.state != 'in_progress':
                raise UserError('Only in-progress requests can be completed.')
            rec.state = 'completed'
            # Add folio line
            folio = rec.folio_id
            if not folio and rec.booking_id and rec.booking_id.folio_id:
                folio = rec.booking_id.folio_id
            if folio:
                pickup_date = rec.pickup_datetime.date() if rec.pickup_datetime else fields.Date.today()
                self.env['hotel.folio.line'].create({
                    'folio_id': folio.id,
                    'description': f"Transport {rec.name} - {rec.get_trip_type_label()}",
                    'category': 'transport',
                    'date': pickup_date,
                    'quantity': 1.0,
                    'unit_price': rec.charge,
                    'reference': rec.name,
                })
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state == 'completed':
                raise UserError('Cannot cancel a completed transport request.')
            rec.state = 'cancelled'
        return True

    def get_trip_type_label(self):
        self.ensure_one()
        labels = {'pickup': 'Pickup', 'drop': 'Drop', 'round': 'Round Trip'}
        return labels.get(self.trip_type, '')

    def action_print_driver_slip(self):
        return self.env.ref('leapai_hotel_management.action_report_driver_slip').report_action(self)
