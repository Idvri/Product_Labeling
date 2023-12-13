# -*- coding: utf-8 -*-

from odoo import fields, models, api


class MarkedProduct(models.Model):
    _name = "marked_product"
    _description = "description"

    name = fields.Char(string='Маркированное название')

    product = fields.Many2one('product', string='Товар', required=False)
    last_stock = fields.Selection([
        ('moscow', 'Склад в Москве'),
        ('batumi', 'Склад в Батуми'),
        ('volgograd', 'Склад в Волгограде')
    ], 'Последний назначенный склад')
    last_status = fields.Selection([
        ('purchase', 'Закупка'),
        ('internal', 'Перемещение'),
        ('promotion', 'Продвижение'),
        ('agency', 'Комиссия агента'),
        ('sold', 'Продано'),
    ], 'Последний назначенный статус')

    costs = fields.One2many('marked_product.costs', 'marked_product', string='Затраты/приходы', required=False)

    profit = fields.Integer(string='Прибыль/убыль RUB', compute='_compute_profit', store=True, readonly=True)
    is_sold = fields.Boolean(default=False)

    @api.depends('costs.count')
    def _compute_profit(self):
        for record in self:
            record.profit = sum(cost.count for cost in record.costs)

    @api.depends('acts')
    def _compute_acts_is_applied(self):
        acts = self.env['act'].search([('marked_products', 'in', [self.id]), ('is_applied', '=', True)])
        self.acts = acts


class MarkedProductCosts(models.Model):
    _name = "marked_product.costs"
    _description = "description"

    marked_product = fields.Many2one('marked_product', 'Marked Product')

    date = fields.Date('Дата создания', readonly=True)
    status = fields.Selection([
        ('purchase', 'Закупка'),
        ('internal', 'Перемещение'),
        ('promotion', 'Продвижение'),
        ('agency', 'Комиссия агента'),
        ('sale', 'Продажа'),
    ], 'Статус')
    count = fields.Float('Значение RUB', readonly=True)
