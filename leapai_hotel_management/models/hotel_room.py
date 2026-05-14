from odoo import models, fields, api


class HotelRoom(models.Model):
    _name = 'hotel.room'
    _description = 'Hotel Room'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Room Number', required=True, tracking=True)
    floor_id = fields.Many2one('hotel.floor', string='Floor', required=True, ondelete='restrict', tracking=True)
    room_type_id = fields.Many2one('hotel.room.type', string='Room Type', required=True, ondelete='restrict', tracking=True)
    status = fields.Selection(
        selection=[
            ('vacant', 'Vacant'),
            ('reserved', 'Reserved'),
            ('occupied', 'Occupied'),
        ],
        string='Status',
        default='vacant',
        readonly=True,
        tracking=True,
    )
    facility_ids = fields.Many2many(
        'hotel.room.facility',
        'hotel_room_facility_rel',
        'room_id',
        'facility_id',
        string='Facilities',
    )
    image_ids = fields.One2many('hotel.room.image', 'room_id', string='Images')
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_floor_unique', 'UNIQUE(name, floor_id)', 'Room number must be unique per floor.'),
    ]


class HotelRoomImage(models.Model):
    _name = 'hotel.room.image'
    _description = 'Hotel Room Image'
    _order = 'sequence, id'

    room_id = fields.Many2one('hotel.room', string='Room', required=True, ondelete='cascade')
    image = fields.Image(string='Image', max_width=1920, max_height=1080)
    name = fields.Char(string='Caption')
    sequence = fields.Integer(string='Sequence', default=10)
