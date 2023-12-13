# -*- coding: utf-8 -*-

from odoo import fields, models


class Product(models.Model):
    _name = "product"
    _description = "description"

    name = fields.Char('Название', required=True, translate=True)
    description = fields.Char('Описание', required=True, translate=True)

    def create_prod(self):
        pass
