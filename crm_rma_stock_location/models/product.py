# -*- coding: utf-8 -*-
# © 2014-2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, fields, models
import openerp.addons.decimal_precision as dp


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    rma_qty_available = fields.Float(
        compute='_compute_rma_template_quantities',
        digits_compute=dp.get_precision('Product Unit of Measure'),
        string='RMA Quantity On Hand'
    )
    rma_virtual_available = fields.Float(
        compute='_compute_rma_template_quantities',
        digits_compute=dp.get_precision('Product Unit of Measure'),
        string='RMA Forecasted Quantity'
    )

    @api.depends('product_variant_ids.rma_qty_available',
                 'product_variant_ids.rma_virtual_available')
    def _compute_rma_template_quantities(self):
        """ Compute rma_qty_available and rma_virtual_available
        with sum of variants quantities.
        """

        for template in self:
            qantities = template.product_variant_ids.read(
                ['rma_qty_available', 'rma_virtual_available']
            )
            template.rma_qty_available = sum(
                qty['rma_qty_available'] for qty in qantities
            )
            template.rma_virtual_available = sum(
                qty['rma_virtual_available'] for qty in qantities
            )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    rma_qty_available = fields.Float(
        compute='_compute_rma_product_quantities',
        digits_compute=dp.get_precision('Product Unit of Measure'),
        string='RMA Quantity On Hand'
    )
    rma_virtual_available = fields.Float(
        compute='_compute_rma_product_quantities',
        digits_compute=dp.get_precision('Product Unit of Measure'),
        string='RMA Forecasted Quantity'
    )

    @api.depends()
    def _compute_rma_product_quantities(self):
        """ Compute both rma_qty_available and rma_virtual_available values
        by calling product_product._product_available with RMA locations
        in context.
        """
        warehouse_model = self.env['stock.warehouse']

        locations = self.env['stock.location']

        warehouse_id = self.env.context.get('warehouse_id')
        if warehouse_id:
            warehouse = warehouse_model.browse(warehouse_id)
            if warehouse.lot_rma_id:
                locations |= warehouse.lot_rma_id

        else:
            warehouses = warehouse_model.search([('lot_rma_id', '!=', False)])
            locations |= warehouses.mapped('lot_rma_id')

        if locations:
            result = self.with_context(
                # Sorted by parent_left to avoid a little Odoo bug
                # in tests environnement
                # see https://github.com/odoo/odoo/pull/11996
                location=locations.sorted(
                    lambda l: l.parent_left
                ).mapped('id'),
            )._product_available()

        else:
            result = {}

        for product in self:
            try:
                product_qties = result[product.id]
            except KeyError:
                product.rma_qty_available = 0
                product.rma_virtual_available = 0

            else:
                product.rma_qty_available = product_qties['qty_available']
                product.rma_virtual_available = product_qties[
                    'virtual_available'
                ]
