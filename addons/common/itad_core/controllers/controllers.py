# from odoo import http


# class ItadCore(http.Controller):
#     @http.route('/itad_core/itad_core', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/itad_core/itad_core/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('itad_core.listing', {
#             'root': '/itad_core/itad_core',
#             'objects': http.request.env['itad_core.itad_core'].search([]),
#         })

#     @http.route('/itad_core/itad_core/objects/<model("itad_core.itad_core"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('itad_core.object', {
#             'object': obj
#         })

