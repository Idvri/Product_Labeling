# -*- coding: utf-8 -*-
import random

from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ActProducts(models.Model):
    _name = "act.products"
    _description = "description"

    product = fields.Many2one('product', 'Товары')
    amount = fields.Integer('Кол-во')

    act = fields.Many2one('act', 'Акт')


class ActCosts(models.Model):
    _name = "act.costs"
    _description = "description"

    status = fields.Selection([
        ('purchase', 'Закупка'),
        ('internal', 'Перемещение'),
        ('promotion', 'Продвижение'),
        ('agency', 'Комиссия агента'),
        ('sale', 'Продажа'),
    ], 'Статус')

    count = fields.Integer('Значение RUB')

    act = fields.Many2one('act', 'Акт')


class Act(models.Model):
    _name = "act"
    _description = "description"

    stocks = [
        ('none', ''),
        ('moscow', 'Склад в Москве'),
        ('batumi', 'Склад в Батуми'),
        ('volgograd', 'Склад в Волгограде')
    ]

    name = fields.Char('Название', default="Акт изменения свойств товаров #")
    create_date = fields.Date('Дата создания', default=lambda self: fields.Date.today())
    status = fields.Selection([
        ('purchase', 'Закупка'),
        ('internal', 'Перемещение'),
        ('promotion', 'Продвижение'),
        ('agency', 'Комиссия агента'),
        ('sale', 'Продажа'),
    ], 'Статус')

    stock_from = fields.Selection(stocks[1:], 'Склад хранения на момент создания акта', default='moscow', required=True)
    stock_to = fields.Selection(stocks, 'Склад назначения', default='moscow', required=True)

    products = fields.One2many('act.products', 'act', string='Товары', required=False)
    marked_products = fields.Many2many('marked_product', string='Маркированные товары',
                                       domain="[('is_sold', '=', False)]", required=False)

    costs = fields.One2many('act.costs', 'act', string='Затраты/приходы', required=False)

    is_applied = fields.Boolean(default=False)

    @api.onchange('status')
    def _onchange_status(self):
        if self.status == 'purchase':
            self._fields['stock_from'].required = False
            self._fields['stock_to'].required = True
        elif self.status == 'internal':
            self._fields['stock_from'].required = True
            self._fields['stock_to'].required = True
        else:
            self._fields['stock_from'].required = False
            self._fields['stock_to'].required = False

    @api.onchange('stock_from', 'stock_to')
    def _onchange_stock_from(self):
        if self.stock_from and self.stock_from != self.stock_to and self.status == 'internal':
            self.marked_products = self.env['marked_product'].search([('last_stock', 'in', [self.stock_from]),
                                                                      ('is_sold', '=', False)])
        elif self.status == 'purchase':
            self.marked_products = self.env['marked_product'].search([('last_stock', 'in', [self.stock_from]),
                                                                      ('is_sold', '=', False)])
        else:
            self.stock_to = 'none'
            self.marked_products = self.env['marked_product'].search([('last_stock', 'in', [self.stock_from]),
                                                                      ('is_sold', '=', False)])

    def create_act(self):
        pass

    @api.model
    def create(self, vals):
        vals['name'] = "Акт изменения свойств товаров #"
        last_record = self.env['act'].search([], order='id desc', limit=1)
        if last_record:
            vals['name'] += str(last_record.id)
        else:
            vals['name'] += '1'

        if vals['status'] == 'purchase':

            if not vals['stock_to'] or vals['stock_to'] == 'none':
                raise ValidationError("Выберите склад!")

            if not vals['products']:
                raise ValidationError("Выберите товар!")

            for product in vals['products']:
                if product[2]['amount'] <= 0:
                    raise ValidationError("Нужно указать корректное кол-во товаров для закупки!")

            if not vals['costs']:
                raise ValidationError("Укажите затраты/приходы!")

            if len(vals['costs']) > 1 or vals['costs'][0][2]['status'] != vals['status']:
                raise ValidationError('При выборе статуса "Закупка" значение поля "Затраты/приходы"'
                                      ' может быть только аналогичным и не более 1 записи за раз!')

            if vals['costs'][0][2]['count'] <= 0:
                raise ValidationError("Необходимо указать сумму больше 0!")

            return super(Act, self).create(vals)

        elif vals['status'] == 'internal':

            if vals['stock_to'] == 'none':
                raise ValidationError("Укажите склад для перемещения!")

            if len(vals['marked_products']) == 0:
                raise ValidationError("Укажите маркированные продукты для возможности проведения акта!")

            for val in vals['marked_products']:
                marked_product = self.env['marked_product'].search([('id', '=', val[1])])

                if vals['stock_from'] != marked_product.last_stock:
                    raise ValidationError(f"Перемещение товара не может быть осуществлено из склада, в котором "
                                          f"отсутвует указанный товар! Вы можете удалить '{marked_product.name}' "
                                          f"или выбрать другой город.")

                if vals['stock_to'] == marked_product.last_stock or vals['stock_from'] == vals['stock_to']:
                    raise ValidationError(f"Перемещение не может быть осуществлено в один и тот же склад! "
                                          f"Вы можете удалить '{marked_product.name}' или выбрать другой город.")

            if not vals['costs']:
                raise ValidationError("Укажите затраты/приходы!")

            if len(vals['costs']) > 1 or vals['costs'][0][2]['status'] != vals['status']:
                raise ValidationError('При выборе статуса "Перемещение" значение поля "Затраты/приходы"'
                                      ' может быть только аналогичным и не более 1 записи за раз!')

            if vals['costs'][0][2]['count'] <= 0:
                raise ValidationError("Необходимо указать сумму больше 0!")

            return super(Act, self).create(vals)

        elif vals['status'] == 'sale':

            if len(vals['marked_products']) == 0:
                raise ValidationError("Укажите маркированные продукты для возможности проведения акта!")

            for val in vals['marked_products']:
                marked_product = self.env['marked_product'].search([('id', 'in', [val[1]])])

                if vals['stock_from'] != marked_product.last_stock:
                    raise ValidationError(f"Указан товар с другого склада '{marked_product.name}'."
                                          f" Вы можете удалить его или выбрать другой склад.")

            if not vals['costs'] or not vals['costs'][0][2]['status']:
                raise ValidationError("Укажите затраты/приходы!")

            if len(vals['costs']) == 1 and vals['costs'][0][2]['status'] == 'sale':

                if vals['costs'][0][2]['count'] <= 0:
                    raise ValidationError(f"Необходимо указать сумму больше 0 для "
                                          f"{vals['costs'][0][2]['status']}!")

                return super(Act, self).create(vals)

            if len(vals['costs']) == 1 and vals['costs'][0][2]['status'] == 'agency':
                raise ValidationError('При выборе статуса "Продажа" значением при указании 1 поля "Затраты/приходы"'
                                      ' может быть только "Продажа"!')

            if len(vals['costs']) > 2:
                raise ValidationError('При выборе статуса "Продажа" значением полей "Затраты/приходы"'
                                      ' может быть "Продажа" либо "Оплата агенту" и не более 1 записи одного вида '
                                      'за раз! Таким образом возможны только 2 записи разного вида.')

            if vals['costs'][0][2]['status'] == vals['costs'][1][2]['status']:
                raise ValidationError('При выборе статуса "Продажа" значением полей "Затраты/приходы"'
                                      ' может быть "Продажа" либо "Оплата агенту" и не более 1 записи одного вида '
                                      'за раз!')

            for cost in vals['costs']:

                if cost[2]['status'] not in ['agency', 'sale']:
                    raise ValidationError('При выборе статуса "Продажа" значением полей "Затраты/приходы"'
                                          ' может быть "Продажа" либо "Оплата агенту" и не более 1 записи одного вида '
                                          'за раз!')

                if cost[2]['count'] <= 0:
                    raise ValidationError(f"Необходимо указать сумму больше 0 для {cost[2]['status']}!")

            return super(Act, self).create(vals)

        else:

            if len(vals['marked_products']) == 0:
                raise ValidationError("Укажите маркированные продукты для возможности проведения акта!")

            for val in vals['marked_products']:
                marked_product = self.env['marked_product'].search([('id', 'in', [val[1]])])

                if vals['stock_from'] != marked_product.last_stock:
                    raise ValidationError(f"Указан товар с другого склада '{marked_product.name}'."
                                          f" Вы можете удалить его или выбрать другой склад.")

            if len(vals['costs']) > 1 or vals['costs'][0][2]['status'] != vals['status']:
                raise ValidationError(f'Значение поля "Затраты/приходы может быть только аналогичным статусу и хранить '
                                      f'не более 1 записи за раз!')

            if vals['costs'][0][2]['count'] <= 0:
                raise ValidationError("Необходимо указать сумму больше 0!")

            return super(Act, self).create(vals)

    def to_apply(self):

        if self.status == "purchase":
            all_amount = 0

            for product in self.products:
                all_amount += product.amount

            product_price = self.costs.count / all_amount
            self.costs.count = -self.costs.count

            marked_product_costs_data = {
                'date': self.create_date,
                'status': self.status,
                'count': -round(product_price),
            }

            for product in self.products:
                amount = product.amount
                product = self.env['product'].search([('id', 'in', [product.product.id])])

                marked_product_data = {
                    'product': product.id,
                    'last_stock': self.stock_to,
                    'last_status': self.status,
                }

                for _ in range(amount):
                    marked_product_data['name'] = f'{product.name} #{random.randint(10000, 99999)}'
                    marked_product = self.env['marked_product'].create(marked_product_data)
                    self.marked_products = [(4, marked_product.id)]

                    marked_product_costs_data['marked_product'] = marked_product.id
                    self.env['marked_product.costs'].create(marked_product_costs_data)

            self.is_applied = True

        elif self.status == "internal":

            internal_price = self.costs.count / len(self.marked_products)
            self.costs.count = -self.costs.count
            marked_product_costs_data = {
                'date': self.create_date,
                'status': self.status,
                'count': -round(internal_price),
            }

            for item in self.marked_products:
                marked_product = self.env['marked_product'].search([('id', 'in', [item.id])])
                marked_product.last_stock = self.stock_to
                marked_product.last_status = self.status

                marked_product_costs_data['marked_product'] = marked_product.id
                self.env['marked_product.costs'].create(marked_product_costs_data)

            self.is_applied = True

        elif self.status == "sale":

            if len(self.costs) == 1:

                internal_price = self.costs.count / len(self.marked_products)
                marked_product_costs_data = {
                    'date': self.create_date,
                    'status': self.status,
                    'count': round(internal_price),
                }

                for item in self.marked_products:
                    marked_product = self.env['marked_product'].search([('id', 'in', [item.id])])
                    marked_product.last_status = 'sold'
                    marked_product.is_sold = True

                    marked_product_costs_data['marked_product'] = marked_product.id
                    self.env['marked_product.costs'].create(marked_product_costs_data)

                self.is_applied = True

            elif self.costs[0].status == "sale":

                internal_price = self.costs[1].count / len(self.marked_products)
                self.costs[1].count = -self.costs[1].count
                marked_product_costs_data = {
                    'date': self.create_date,
                    'status': self.costs[1].status,
                    'count': -round(internal_price),
                }

                for item in self.marked_products:
                    marked_product = self.env['marked_product'].search([('id', 'in', [item.id])])
                    marked_product.last_status = self.costs[1].status

                    marked_product_costs_data['marked_product'] = marked_product.id
                    self.env['marked_product.costs'].create(marked_product_costs_data)

                internal_price = self.costs[0].count / len(self.marked_products)
                marked_product_costs_data = {
                    'date': self.create_date,
                    'status': self.costs[0].status,
                    'count': round(internal_price),
                }

                for item in self.marked_products:
                    marked_product = self.env['marked_product'].search([('id', 'in', [item.id])])
                    marked_product.last_status = 'sold'
                    marked_product.is_sold = True

                    marked_product_costs_data['marked_product'] = marked_product.id
                    self.env['marked_product.costs'].create(marked_product_costs_data)

                self.is_applied = True

            else:

                internal_price = self.costs[0].count / len(self.marked_products)
                self.costs[0].count = -self.costs[0].count
                marked_product_costs_data = {
                    'date': self.create_date,
                    'status': self.costs[0].status,
                    'count': -round(internal_price),
                }

                for item in self.marked_products:
                    marked_product = self.env['marked_product'].search([('id', 'in', [item.id])])
                    marked_product.last_status = self.costs[0].status

                    marked_product_costs_data['marked_product'] = marked_product.id
                    self.env['marked_product.costs'].create(marked_product_costs_data)

                internal_price = self.costs[1].count / len(self.marked_products)
                marked_product_costs_data = {
                    'date': self.create_date,
                    'status': self.costs[1].status,
                    'count': round(internal_price),
                }

                for item in self.marked_products:
                    marked_product = self.env['marked_product'].search([('id', 'in', [item.id])])
                    marked_product.last_status = 'sold'
                    marked_product.is_sold = True

                    marked_product_costs_data['marked_product'] = marked_product.id
                    self.env['marked_product.costs'].create(marked_product_costs_data)

                self.is_applied = True

        else:

            internal_price = self.costs.count / len(self.marked_products)
            self.costs.count = -self.costs.count
            marked_product_costs_data = {
                'date': self.create_date,
                'status': self.status,
                'count': -round(internal_price),
            }

            for item in self.marked_products:
                marked_product = self.env['marked_product'].search([('id', 'in', [item.id])])
                marked_product.last_status = self.status

                marked_product_costs_data['marked_product'] = marked_product.id
                self.env['marked_product.costs'].create(marked_product_costs_data)

            self.is_applied = True
