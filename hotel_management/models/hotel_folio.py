from odoo import models, fields, api


class HotelFolio(models.Model):
    _name = 'hotel.folio'
    _description = 'Hotel Folio'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Folio Number',
        readonly=True,
        default='New',
        copy=False,
        tracking=True,
    )
    booking_id = fields.Many2one('hotel.booking', string='Booking', ondelete='restrict')
    guest_name = fields.Char(string='Guest Name', related='booking_id.guest_name', store=True)
    check_in = fields.Date(string='Check-In Date')
    check_out = fields.Date(string='Check-Out Date')
    state = fields.Selection(
        selection=[
            ('open', 'Open'),
            ('closed', 'Closed'),
        ],
        string='Status',
        default='open',
        tracking=True,
    )
    line_ids = fields.One2many('hotel.folio.line', 'folio_id', string='Charges')
    total_amount = fields.Float(
        string='Total Amount',
        digits=(16, 2),
        compute='_compute_total_amount',
        store=True,
    )
    notes = fields.Text(string='Notes')

    @api.depends('line_ids.amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.folio') or 'New'
        return super().create(vals_list)

    def action_close(self):
        for rec in self:
            rec.state = 'closed'
        return True

    def action_reopen(self):
        for rec in self:
            rec.state = 'open'
        return True

    def action_print_invoice(self):
        return self.env.ref('hotel_management.action_report_hotel_invoice').report_action(self)


class HotelFolioLine(models.Model):
    _name = 'hotel.folio.line'
    _description = 'Hotel Folio Line'
    _order = 'date, id'

    folio_id = fields.Many2one('hotel.folio', string='Folio', required=True, ondelete='cascade')
    booking_room_id = fields.Many2one('hotel.booking.room', string='Booking Room', ondelete='set null')
    description = fields.Char(string='Description', required=True)
    category = fields.Selection(
        selection=[
            ('room', 'Room'),
            ('laundry', 'Laundry'),
            ('restaurant', 'Restaurant'),
            ('transport', 'Transport'),
            ('extra', 'Extra Services'),
        ],
        string='Category',
        required=True,
    )
    date = fields.Date(string='Date', default=fields.Date.today)
    quantity = fields.Float(string='Quantity', default=1.0)
    unit_price = fields.Float(string='Unit Price', digits=(16, 2))
    amount = fields.Float(
        string='Amount',
        digits=(16, 2),
        compute='_compute_amount',
        store=True,
    )
    reference = fields.Char(string='Reference')

    @api.depends('quantity', 'unit_price')
    def _compute_amount(self):
        for rec in self:
            rec.amount = (rec.quantity or 0.0) * (rec.unit_price or 0.0)
