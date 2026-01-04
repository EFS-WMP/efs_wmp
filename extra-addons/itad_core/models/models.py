# from odoo import models, fields, api


# class itad_core(models.Model):
#     _name = 'itad_core.itad_core'
#     _description = 'itad_core.itad_core'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

