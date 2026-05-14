from odoo import models, fields, api, exceptions
from odoo.exceptions import UserError, ValidationError


class HotelBooking(models.Model):
    _name = 'hotel.booking'
    _description = 'Hotel Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Booking Reference',
        readonly=True,
        default='New',
        copy=False,
        tracking=True,
    )
    guest_name = fields.Char(string='Guest Name', required=True, tracking=True)
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    check_in = fields.Date(string='Check-In Date', required=True, tracking=True)
    check_out = fields.Date(string='Check-Out Date', required=True, tracking=True)
    adults = fields.Integer(string='Adults', default=1)
    children = fields.Integer(string='Children', default=0)
    total_guests = fields.Integer(
        string='Total Guests',
        compute='_compute_total_guests',
        store=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirm', 'Confirmed'),
            ('check_in', 'Checked In'),
            ('check_out', 'Checked Out'),
            ('cancel', 'Cancelled'),
            ('no_show', 'No Show'),
        ],
        string='Status',
        default='draft',
        tracking=True,
    )
    room_ids = fields.One2many('hotel.booking.room', 'booking_id', string='Rooms')
    guest_ids = fields.One2many('hotel.booking.guest', 'booking_id', string='Guests')
    room_change_ids = fields.One2many('hotel.booking.room.change', 'booking_id', string='Room Changes')
    folio_id = fields.Many2one('hotel.folio', string='Folio', readonly=True, copy=False)
    notes = fields.Text(string='Internal Notes')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    room_count = fields.Integer(string='Room Count', compute='_compute_counts')
    laundry_count = fields.Integer(string='Laundry Orders', compute='_compute_counts')
    restaurant_count = fields.Integer(string='Restaurant Orders', compute='_compute_counts')
    transport_count = fields.Integer(string='Transport Requests', compute='_compute_counts')

    @api.depends('adults', 'children')
    def _compute_total_guests(self):
        for rec in self:
            rec.total_guests = (rec.adults or 0) + (rec.children or 0)

    @api.depends('room_ids')
    def _compute_counts(self):
        for rec in self:
            rec.room_count = len(rec.room_ids)
            if rec.id:
                rec.laundry_count = self.env['hotel.laundry.order'].search_count([('booking_id', '=', rec.id)])
                rec.restaurant_count = self.env['hotel.restaurant.order'].search_count([('booking_id', '=', rec.id)])
                rec.transport_count = self.env['hotel.transport.request'].search_count([('booking_id', '=', rec.id)])
            else:
                rec.laundry_count = 0
                rec.restaurant_count = 0
                rec.transport_count = 0

    @api.constrains('check_in', 'check_out')
    def _check_dates(self):
        for rec in self:
            if rec.check_in and rec.check_out and rec.check_out <= rec.check_in:
                raise ValidationError('Check-Out date must be after Check-In date.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.booking') or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only draft bookings can be confirmed.')
            rec.state = 'confirm'
            for room_line in rec.room_ids:
                room_line.room_id.write({'status': 'reserved'})
        return True

    def action_check_in(self):
        for rec in self:
            if rec.state != 'confirm':
                raise UserError('Only confirmed bookings can be checked in.')
            rec.state = 'check_in'
            for room_line in rec.room_ids:
                room_line.room_id.write({'status': 'occupied'})
            # Create folio
            folio = self.env['hotel.folio'].create({
                'booking_id': rec.id,
                'guest_name': rec.guest_name,
                'check_in': rec.check_in,
                'check_out': rec.check_out,
            })
            # Create folio lines for rooms
            for room_line in rec.room_ids:
                nights = room_line.nights or 1
                description = (
                    f"Room {room_line.room_id.name} - {nights} night(s) "
                    f"@ {room_line.rate_per_night:.2f}/night"
                )
                self.env['hotel.folio.line'].create({
                    'folio_id': folio.id,
                    'booking_room_id': room_line.id,
                    'description': description,
                    'category': 'room',
                    'date': rec.check_in,
                    'quantity': nights,
                    'unit_price': room_line.rate_per_night,
                })
            rec.folio_id = folio.id
        return True

    def action_check_out(self):
        for rec in self:
            if rec.state != 'check_in':
                raise UserError('Only checked-in bookings can be checked out.')
            rec.state = 'check_out'
            for room_line in rec.room_ids:
                room_line.room_id.write({'status': 'vacant'})
            if rec.folio_id:
                rec.folio_id.write({'state': 'closed', 'check_out': rec.check_out})
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state in ('check_out',):
                raise UserError('Cannot cancel a completed booking.')
            for room_line in rec.room_ids:
                room_line.room_id.write({'status': 'vacant'})
            rec.state = 'cancel'
        return True

    def action_no_show(self):
        for rec in self:
            if rec.state != 'confirm':
                raise UserError('Only confirmed bookings can be marked as No Show.')
            for room_line in rec.room_ids:
                room_line.room_id.write({'status': 'vacant'})
            rec.state = 'no_show'
        return True

    def action_reset_draft(self):
        for rec in self:
            if rec.state not in ('cancel', 'no_show'):
                raise UserError('Only cancelled or no-show bookings can be reset to draft.')
            rec.state = 'draft'
        return True

    def action_extend_checkout(self, new_date):
        self.ensure_one()
        if not new_date:
            raise UserError('Please provide a new check-out date.')
        self.check_out = new_date
        for room_line in self.room_ids:
            room_line._compute_nights()
            room_line._compute_room_subtotal()
        # Update folio room lines
        if self.folio_id:
            for room_line in self.room_ids:
                folio_line = self.env['hotel.folio.line'].search([
                    ('folio_id', '=', self.folio_id.id),
                    ('booking_room_id', '=', room_line.id),
                    ('category', '=', 'room'),
                ], limit=1)
                if folio_line:
                    nights = room_line.nights or 1
                    description = (
                        f"Room {room_line.room_id.name} - {nights} night(s) "
                        f"@ {room_line.rate_per_night:.2f}/night"
                    )
                    folio_line.write({
                        'quantity': nights,
                        'description': description,
                    })
        return True

    def action_view_folio(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Folio',
            'res_model': 'hotel.folio',
            'view_mode': 'form',
            'res_id': self.folio_id.id,
        }

    def action_view_laundry(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Laundry Orders',
            'res_model': 'hotel.laundry.order',
            'view_mode': 'list,form',
            'domain': [('booking_id', '=', self.id)],
            'context': {'default_booking_id': self.id},
        }

    def action_view_restaurant(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Restaurant Orders',
            'res_model': 'hotel.restaurant.order',
            'view_mode': 'list,form',
            'domain': [('booking_id', '=', self.id)],
            'context': {'default_booking_id': self.id},
        }

    def action_view_transport(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transport Requests',
            'res_model': 'hotel.transport.request',
            'view_mode': 'list,form',
            'domain': [('booking_id', '=', self.id)],
            'context': {'default_booking_id': self.id},
        }


class HotelBookingRoom(models.Model):
    _name = 'hotel.booking.room'
    _description = 'Hotel Booking Room Line'
    _order = 'id'

    booking_id = fields.Many2one('hotel.booking', string='Booking', required=True, ondelete='cascade')
    room_id = fields.Many2one('hotel.room', string='Room', required=True, ondelete='restrict')
    check_in = fields.Date(string='Check-In', related='booking_id.check_in', store=True)
    check_out = fields.Date(string='Check-Out', related='booking_id.check_out', store=True)
    nights = fields.Integer(
        string='Nights',
        compute='_compute_nights',
        store=True,
    )
    rate_per_night = fields.Float(
        string='Rate / Night',
        digits=(16, 2),
        compute='_compute_rate_per_night',
        store=True,
        readonly=False,
    )
    extra_person_count = fields.Integer(string='Extra Persons', default=0)
    extra_person_charge = fields.Float(string='Extra Person Charge', digits=(16, 2), default=0.0)
    room_subtotal = fields.Float(
        string='Subtotal',
        digits=(16, 2),
        compute='_compute_room_subtotal',
        store=True,
    )
    notes = fields.Text(string='Notes')

    @api.depends('booking_id.check_in', 'booking_id.check_out')
    def _compute_nights(self):
        for rec in self:
            if rec.booking_id.check_in and rec.booking_id.check_out:
                delta = rec.booking_id.check_out - rec.booking_id.check_in
                rec.nights = delta.days
            else:
                rec.nights = 0

    @api.depends('room_id', 'booking_id.check_in')
    def _compute_rate_per_night(self):
        for rec in self:
            if not rec.room_id:
                rec.rate_per_night = 0.0
                continue
            # Look up seasonal rate
            check_in = rec.booking_id.check_in
            room_type = rec.room_id.room_type_id
            rate = 0.0
            if check_in and room_type:
                seasonal = self.env['hotel.seasonal.rate'].search([
                    ('room_type_id', '=', room_type.id),
                    ('date_from', '<=', check_in),
                    ('date_to', '>=', check_in),
                ], limit=1)
                if seasonal:
                    rate = seasonal.price_per_night
                else:
                    rate = room_type.base_price
            rec.rate_per_night = rate

    @api.depends('nights', 'rate_per_night', 'extra_person_count', 'extra_person_charge')
    def _compute_room_subtotal(self):
        for rec in self:
            room_charge = (rec.nights or 0) * (rec.rate_per_night or 0.0)
            extra_charge = (rec.extra_person_count or 0) * (rec.extra_person_charge or 0.0)
            rec.room_subtotal = room_charge + extra_charge


class HotelBookingGuest(models.Model):
    _name = 'hotel.booking.guest'
    _description = 'Hotel Booking Guest'
    _order = 'name'

    booking_id = fields.Many2one('hotel.booking', string='Booking', required=True, ondelete='cascade')
    room_id = fields.Many2one('hotel.room', string='Room', ondelete='restrict')
    name = fields.Char(string='Guest Name', required=True)
    document_type_id = fields.Many2one('hotel.document.type', string='Document Type', ondelete='restrict')
    document_number = fields.Char(string='Document Number')
    document_file = fields.Binary(string='Document Scan', attachment=True)
    document_filename = fields.Char(string='Filename')


class HotelBookingRoomChange(models.Model):
    _name = 'hotel.booking.room.change'
    _description = 'Hotel Booking Room Change'
    _order = 'change_date desc'

    booking_id = fields.Many2one('hotel.booking', string='Booking', required=True, ondelete='cascade')
    room_from_id = fields.Many2one('hotel.room', string='From Room', required=True, ondelete='restrict')
    room_to_id = fields.Many2one('hotel.room', string='To Room', required=True, ondelete='restrict')
    change_date = fields.Datetime(string='Change Date', default=fields.Datetime.now)
    reason = fields.Text(string='Reason', required=True)
    user_id = fields.Many2one('res.users', string='Changed By', default=lambda self: self.env.user)
