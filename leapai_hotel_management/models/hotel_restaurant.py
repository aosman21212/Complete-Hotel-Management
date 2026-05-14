from odoo import models, fields, api
from odoo.exceptions import UserError


class HotelRestaurantOrder(models.Model):
    _name = 'hotel.restaurant.order'
    _description = 'Hotel Restaurant Order'
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
            ('confirmed', 'Confirmed'),
            ('in_preparation', 'In Preparation'),
            ('delivered', 'Delivered'),
        ],
        string='Status',
        default='draft',
        tracking=True,
    )
    line_ids = fields.One2many('hotel.restaurant.order.line', 'order_id', string='Items')
    total_amount = fields.Float(
        string='Total Amount',
        digits=(16, 2),
        compute='_compute_total_amount',
        store=True,
    )
    notes = fields.Text(string='Notes')
    order_date = fields.Datetime(string='Order Date', default=fields.Datetime.now)

    @api.depends('line_ids.subtotal')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('subtotal'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.restaurant.order') or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only draft orders can be confirmed.')
            rec.state = 'confirmed'
        return True

    def action_prepare(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError('Only confirmed orders can be put into preparation.')
            rec.state = 'in_preparation'
        return True

    def action_deliver(self):
        for rec in self:
            if rec.state != 'in_preparation':
                raise UserError('Only in-preparation orders can be delivered.')
            rec.state = 'delivered'
            # Add folio line
            folio = rec.folio_id
            if not folio and rec.booking_id and rec.booking_id.folio_id:
                folio = rec.booking_id.folio_id
            if folio:
                order_date = rec.order_date.date() if rec.order_date else fields.Date.today()
                self.env['hotel.folio.line'].create({
                    'folio_id': folio.id,
                    'description': f"Restaurant Order {rec.name}",
                    'category': 'restaurant',
                    'date': order_date,
                    'quantity': 1.0,
                    'unit_price': rec.total_amount,
                    'reference': rec.name,
                })
        return True


class HotelRestaurantOrderLine(models.Model):
    _name = 'hotel.restaurant.order.line'
    _description = 'Hotel Restaurant Order Line'
    _order = 'id'

    order_id = fields.Many2one('hotel.restaurant.order', string='Order', required=True, ondelete='cascade')
    product_name = fields.Char(string='Item', required=True)
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
