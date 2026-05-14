from odoo import models, fields


class HotelFloor(models.Model):
    _name = 'hotel.floor'
    _description = 'Hotel Floor'
    _order = 'sequence, name'

    name = fields.Char(string='Floor Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Floor name must be unique.'),
    ]


class HotelRoomType(models.Model):
    _name = 'hotel.room.type'
    _description = 'Hotel Room Type'
    _order = 'name'

    name = fields.Char(string='Room Type', required=True)
    description = fields.Text(string='Description')
    capacity_adults = fields.Integer(string='Adult Capacity', default=2)
    capacity_children = fields.Integer(string='Child Capacity', default=1)
    base_price = fields.Float(string='Base Price / Night', digits=(16, 2))
    active = fields.Boolean(string='Active', default=True)


class HotelRoomFacility(models.Model):
    _name = 'hotel.room.facility'
    _description = 'Hotel Room Facility'
    _order = 'name'

    name = fields.Char(string='Facility', required=True)
    icon = fields.Char(string='Icon Class', default='fa-check', help='FontAwesome icon class, e.g. fa-wifi')


class HotelDocumentType(models.Model):
    _name = 'hotel.document.type'
    _description = 'Guest Document Type'
    _order = 'name'

    name = fields.Char(string='Document Type', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)


class HotelTransportLocation(models.Model):
    _name = 'hotel.transport.location'
    _description = 'Transport Location'
    _order = 'name'

    name = fields.Char(string='Location Name', required=True)
    address = fields.Char(string='Address')
    distance_km = fields.Float(string='Distance from Hotel (KM)', digits=(16, 2))
    price_per_km = fields.Float(string='Price per KM', digits=(16, 2))


class HotelSeasonalRate(models.Model):
    _name = 'hotel.seasonal.rate'
    _description = 'Hotel Seasonal Rate'
    _order = 'date_from'

    name = fields.Char(string='Rate Name', required=True)
    room_type_id = fields.Many2one('hotel.room.type', string='Room Type', required=True, ondelete='cascade')
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    price_per_night = fields.Float(string='Price per Night', digits=(16, 2), required=True)
    description = fields.Text(string='Description')
