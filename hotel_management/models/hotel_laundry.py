from odoo import models, fields, api
from odoo.exceptions import UserError


class HotelLaundryOrder(models.Model):
    _name = 'hotel.laundry.order'
    _description = 'Hotel Laundry Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Order Reference',
        readonly=True,
        default='New',
        copy=False,
        tracking=True,
    )
    booking_id = fields.Many2one('hotel.booking', string='Booking', ondelete='restrict')
    folio_id = fields.Many2one('hotel.folio', string='Folio', ondelete='restrict')
    room_id = fields.Many2one('hotel.room', string='Room', ondelete='restrict')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirm', 'Confirmed'),
            ('pickup', 'Pickup'),
            ('in_process', 'In Process'),
            ('deliver', 'Delivered'),
        ],
        string='Status',
        default='draft',
        tracking=True,
    )
    line_ids = fields.One2many('hotel.laundry.order.line', 'order_id', string='Items')
    total_amount = fields.Float(
        string='Total Amount',
        digits=(16, 2),
        compute='_compute_total_amount',
        store=True,
    )
    notes = fields.Text(string='Notes')
    date = fields.Date(string='Date', default=fields.Date.today)

    @api.depends('line_ids.subtotal')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('subtotal'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.laundry.order') or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only draft orders can be confirmed.')
            rec.state = 'confirm'
        return True

    def action_pickup(self):
        for rec in self:
            if rec.state != 'confirm':
                raise UserError('Only confirmed orders can be picked up.')
            rec.state = 'pickup'
        return True

    def action_in_process(self):
        for rec in self:
            if rec.state != 'pickup':
                raise UserError('Only picked-up orders can be processed.')
            rec.state = 'in_process'
        return True

    def action_deliver(self):
        for rec in self:
            if rec.state != 'in_process':
                raise UserError('Only in-process orders can be delivered.')
            rec.state = 'deliver'
            # Add folio line
            folio = rec.folio_id
            if not folio and rec.booking_id and rec.booking_id.folio_id:
                folio = rec.booking_id.folio_id
            if folio:
                self.env['hotel.folio.line'].create({
                    'folio_id': folio.id,
                    'description': f"Laundry Order {rec.name}",
                    'category': 'laundry',
                    'date': rec.date or fields.Date.today(),
                    'quantity': 1.0,
                    'unit_price': rec.total_amount,
                    'reference': rec.name,
                })
        return True


class HotelLaundryOrderLine(models.Model):
    _name = 'hotel.laundry.order.line'
    _description = 'Hotel Laundry Order Line'
    _order = 'id'

    order_id = fields.Many2one('hotel.laundry.order', string='Order', required=True, ondelete='cascade')
    item_name = fields.Char(string='Item', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Float(string='Unit Price', digits=(16, 2))
    subtotal = fields.Float(
        string='Subtotal',
        digits=(16, 2),
        compute='_compute_subtotal',
        store=True,
    )

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = (rec.quantity or 0.0) * (rec.price_unit or 0.0)
