"""Small offline checks for budget and quote invariants; no live account calls."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/mcd-budget/scripts'))
from mcp_client import Client, MCPError, business_response, decode_response
from plan import money, solve
from quote import checked_quote


class BudgetChecks(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads((ROOT / 'examples/candidates.json').read_text(encoding='utf-8'))

    def test_decimal_and_invalid_money(self):
        self.assertEqual(money('0.10', 'price') + money('0.20', 'price'), Decimal('0.30'))
        for value in ('NaN', 'Infinity', '-1', '0.001', True, None):
            with self.assertRaises(ValueError):
                money(value, 'price')

    def test_combo_does_not_duplicate_side_or_drink(self):
        result = solve(self.doc)
        self.assertTrue(result['plans'])
        for plan in result['plans']:
            if 'demo-meal' in plan['offer_ids']:
                self.assertEqual(plan['offer_ids'], ['demo-meal'])
            self.assertIn('drink', plan['coverage'])
            self.assertEqual(plan['status'], 'needs_live_quote')

    def test_unknown_nutrition_excluded_under_constraint(self):
        self.doc['min_protein_g'] = 1
        for offer in self.doc['offers']:
            offer['protein_g'] = None
        self.assertEqual(solve(self.doc)['candidate_count'], 0)

    def test_same_coupon_not_consumed_twice(self):
        self.doc['offers'] = [x for x in self.doc['offers'] if x['id'] in ('demo-main-a','demo-drink')]
        for offer in self.doc['offers']:
            offer['coupon_ids'] = ['same-coupon']
        self.assertEqual(solve(self.doc)['candidate_count'], 0)

    def test_duplicate_offer_rejected(self):
        self.doc['offers'].append(deepcopy(self.doc['offers'][0]))
        with self.assertRaises(ValueError):
            solve(self.doc)

    def test_overestimate_retained_for_live_discount(self):
        self.doc['budget_yuan'] = '1.00'
        result = solve(self.doc)
        self.assertTrue(result['plans'])
        self.assertFalse(result['plans'][0]['estimated_within_budget'])

    def test_exact_budget_and_over_budget_quote(self):
        items = [{'productCode':'123', 'quantity':1}]
        response = {'price':2500, 'productList':items}
        self.assertEqual(checked_quote(response, items, Decimal('25'))['status'], 'verified_price')
        response['price'] = 2501
        self.assertEqual(checked_quote(response, items, Decimal('25'))['status'], 'over_budget')
        response['price'] = True
        with self.assertRaises(MCPError):
            checked_quote(response, items, Decimal('25'))

    def test_quote_must_contain_same_products_and_quantities(self):
        with self.assertRaises(MCPError):
            checked_quote({'price':100,'productList':[{'productCode':'123','quantity':2}]},
                          [{'productCode':'123','quantity':1}], Decimal('25'))

    def test_sse_matching_id_and_protocol_error(self):
        data = 'event: message\ndata: {"jsonrpc":"2.0","method":"notice"}\n\n'
        data += 'data: {"id":2,"result":{"value":1}}\n\n'
        self.assertEqual(decode_response(data, 2), {'value':1})
        with self.assertRaises(MCPError):
            decode_response('{"id":2,"error":{"code":-1}}', 2)

    def test_business_error_and_write_tool_rejected(self):
        with self.assertRaises(MCPError):
            business_response({'structuredContent':{'success':False,'code':401}})
        with self.assertRaises(MCPError):
            Client('fake-token').call('create-order', {})


if __name__ == '__main__':
    unittest.main()
