{
    'name': 'Hotel Management',
    'version': '19.0.1.0.0',
    'category': 'Industries',
    'summary': 'Complete hospitality operations — rooms, bookings, folios, laundry, restaurant, transport, billing',
    'description': '''
Hotel Management System for Odoo 19
=====================================

A comprehensive hotel management module covering:
- Room and floor management with seasonal pricing
- Booking lifecycle: Draft → Confirmed → Check-In → Check-Out / Cancel / No Show
- Automatic folio creation and real-time charge synchronization
- Laundry service with full workflow tracking
- Restaurant & room service orders
- Transport scheduling with KM-based charges and printable driver slips
- Single or split invoice generation
- Role-based access: Admin, Reception, Laundry, Restaurant

Contact:
  Location  : King Abdulaziz Branch Road, Riyadh, Saudi Arabia
  Email     : sales@leapai.ai
  Phone     : +966 53 553 3627
  Website   : https://leapai.ai
  Developer : Abdulkaraim Osman — Tech Manager | Backend Engineer | DevOps Engineer
              at Bab International Corp For Specialized Services
  LinkedIn  : https://www.linkedin.com/in/abdulkaraim-o-385b7a110/
    ''',
    'author': 'leapai.ai',
    'website': 'https://leapai.ai',
    'support': 'sales@leapai.ai',
    'maintainer': 'Abdulkaraim Osman',
    'depends': ['base', 'mail', 'product', 'uom', 'account'],
    'images': [
        'static/description/screenshots/01_room_overview.jpg',
        'static/description/screenshots/02_bookings_list.jpg',
        'static/description/screenshots/03_booking_form.jpg',
        'static/description/screenshots/04_folio_invoice.jpg',
        'static/description/screenshots/05_laundry_restaurant.jpg',
        'static/description/screenshots/06_transport_driver_slip.jpg',
    ],
    'data': [
        'security/hotel_security.xml',
        'security/ir.model.access.csv',
        'data/hotel_sequence.xml',
        'data/hotel_data.xml',
        'data/hotel_demo_data.xml',
        'views/hotel_floor_views.xml',
        'views/hotel_room_views.xml',
        'views/hotel_booking_views.xml',
        'views/hotel_folio_views.xml',
        'views/hotel_laundry_views.xml',
        'views/hotel_restaurant_views.xml',
        'views/hotel_transport_views.xml',
        'views/hotel_menu.xml',
        'report/hotel_report_templates.xml',
        'report/hotel_invoice_report.xml',
        'report/hotel_driver_slip_report.xml',
    ],
    'demo': [
        'demo/hotel_demo.xml',
    ],
    'application': True,
    'installable': True,
    'post_init_hook': 'post_init_hook',
    'license': 'LGPL-3',
}
