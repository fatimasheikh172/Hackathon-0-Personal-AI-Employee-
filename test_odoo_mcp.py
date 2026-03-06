#!/usr/bin/env python3
"""
Test script for Odoo MCP Server
Tests all major functions in DRY_RUN mode
"""

from odoo_mcp_server import (
    authenticate,
    get_invoices,
    get_financial_summary,
    create_customer,
    create_invoice
)

print("=" * 60)
print("ODOO MCP SERVER - TEST SUITE")
print("=" * 60)

# Test 1: authenticate()
print("\n" + "=" * 60)
print("TEST 1: authenticate()")
print("=" * 60)
auth_result = authenticate()
print(f"\nResult: {auth_result}")

# Test 2: get_invoices()
print("\n" + "=" * 60)
print("TEST 2: get_invoices(status='posted', limit=5)")
print("=" * 60)
invoices_result = get_invoices(status="posted", limit=5)
print(f"\nResult: {invoices_result}")
if invoices_result["success"] and invoices_result["invoices"]:
    print("\nInvoices found:")
    for inv in invoices_result["invoices"]:
        print(f"  - {inv['number']}: {inv['customer']} - ${inv['amount']} ({inv['status']})")

# Test 3: get_financial_summary()
print("\n" + "=" * 60)
print("TEST 3: get_financial_summary()")
print("=" * 60)
financial_result = get_financial_summary()
print(f"\nResult: {financial_result}")
if financial_result["success"]:
    summary = financial_result["summary"]
    print(f"\nFinancial Summary:")
    print(f"  Revenue:  ${summary.get('revenue', 0):.2f}")
    print(f"  Expenses: ${summary.get('expenses', 0):.2f}")
    print(f"  Profit:   ${summary.get('profit', 0):.2f}")

# Test 4: create_customer() - DRY_RUN mode
print("\n" + "=" * 60)
print("TEST 4: create_customer() - DRY_RUN MODE")
print("=" * 60)
customer_result = create_customer("Test Customer Corp", "test@example.com", "+1-555-0123")
print(f"\nResult: {customer_result}")

# Test 5: create_invoice() - DRY_RUN mode
print("\n" + "=" * 60)
print("TEST 5: create_invoice() - DRY_RUN MODE")
print("=" * 60)
invoice_result = create_invoice(
    customer_name="Test Customer Corp",
    amount=250.00,
    description="Consulting Services - March 2026"
)
print(f"\nResult: {invoice_result}")

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print(f"1. authenticate():        {'[PASS]' if auth_result['success'] else '[FAIL]'}")
print(f"2. get_invoices():        {'[PASS]' if invoices_result['success'] else '[FAIL]'}")
print(f"3. get_financial_summary(): {'[PASS]' if financial_result['success'] else '[FAIL]'}")
print(f"4. create_customer():     {'[PASS]' if customer_result['success'] else '[FAIL]'}")
print(f"5. create_invoice():      {'[PASS]' if invoice_result['success'] else '[FAIL]'}")
print("=" * 60)
