"""Browser tests for the Imports page (PLAN.md Phase 5.4). Fixtures live in e2e_support.py."""
from pathlib import Path

import pytest

from e2e_support import base_url, browser, expect, page, sign_in  # noqa: F401

pytestmark = pytest.mark.e2e

FIXTURES = Path(__file__).parent / 'fixtures'
KRAKEN = FIXTURES / 'kraken' / 'ledgers.csv'


def open_import_page(page, base_url):
    page.goto(f'{base_url}/import')
    expect(page.locator('#imports-list-loaded')).to_be_attached()


def choose_file(page, path):
    page.set_input_files('#import-file', str(path))
    page.click('#preview-button')


def test_preview_then_import(page, base_url):
    sign_in(page, base_url)
    open_import_page(page, base_url)
    expect(page.locator('#imports-empty')).to_be_visible()

    choose_file(page, KRAKEN)
    expect(page.locator('#preview')).to_be_visible()
    expect(page.locator('#preview-title')).to_have_text('ledgers.csv · Kraken')
    expect(page.locator('#preview-counts')).to_have_text('5 trades found: 5 new, 0 already in CoinFlow')
    expect(page.locator('#preview-sides')).to_have_text('3 buys · 1 sale · 1 reward')
    expect(page.locator('#preview-dates')).to_have_text('Jan 5, 2024 – May 20, 2024')
    expect(page.locator('#preview-problem')).to_be_hidden()

    # Skipped rows are listed with their line number and reason
    expect(page.locator('#preview-skipped summary')).to_have_text('6 rows skipped')
    page.click('#preview-skipped summary')
    expect(page.locator('#preview-skipped li').first).to_have_text(
        'Line 2: Deposit (moving money in or out of Kraken does not change what you paid for BTC)')

    expect(page.locator('#import-confirm')).to_have_text('Import 5 trades')
    page.click('#import-confirm')
    expect(page.locator('#preview')).to_be_hidden()
    expect(page.locator('#imports-body tr')).to_have_count(1)
    row = page.locator('#imports-body tr').first
    expect(row).to_contain_text('ledgers.csv')
    expect(row).to_contain_text('Kraken')
    expect(row.locator('.cell-trades')).to_have_text('5')

    # The trades are now in the ledger
    page.goto(f'{base_url}/')
    page.click('#tab-transactions-button')
    expect(page.locator('#transactions-body tr')).to_have_count(5)


def test_problem_blocks_the_import(page, base_url, tmp_path):
    lines = KRAKEN.read_text().splitlines()
    only_the_sale = tmp_path / 'sale.csv'
    only_the_sale.write_text('\n'.join([lines[0], lines[12], lines[13]]) + '\n')

    sign_in(page, base_url)
    open_import_page(page, base_url)
    choose_file(page, only_the_sale)
    expect(page.locator('#preview-problem')).to_be_visible()
    expect(page.locator('#preview-problem')).to_contain_text('only 0 BTC is held')
    expect(page.locator('#import-confirm')).to_be_disabled()


def test_same_file_twice(page, base_url):
    sign_in(page, base_url)
    open_import_page(page, base_url)
    choose_file(page, KRAKEN)
    page.click('#import-confirm')
    expect(page.locator('#imports-body tr')).to_have_count(1)
    expect(page.locator('.swal2-container')).to_have_count(0)

    choose_file(page, KRAKEN)
    expect(page.locator('#preview-problem')).to_contain_text('already imported')
    expect(page.locator('#import-confirm')).to_be_disabled()


def test_unsupported_file_is_explained(page, base_url, tmp_path):
    other = tmp_path / 'bank.csv'
    other.write_text('date,amount\n2024-01-01,5\n')
    sign_in(page, base_url)
    open_import_page(page, base_url)
    choose_file(page, other)
    expect(page.locator('.swal2-html-container')).to_contain_text("isn't a Kraken or Coinbase export")
    expect(page.locator('#preview')).to_be_hidden()


def test_remove_an_import(page, base_url):
    sign_in(page, base_url)
    open_import_page(page, base_url)
    choose_file(page, KRAKEN)
    page.click('#import-confirm')
    expect(page.locator('#imports-body tr')).to_have_count(1)
    expect(page.locator('.swal2-container')).to_have_count(0)

    page.click('#imports-body tr .delete-button')
    page.click('.swal2-confirm')
    expect(page.locator('#imports-body tr')).to_have_count(0)
    expect(page.locator('#imports-empty')).to_be_visible()
