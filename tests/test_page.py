import pytest
from flask import Flask
from web.utils.pagination import Pagination, get_pagination_args, paginate


def test_pagination_init():
    items = list(range(100))
    pagination = Pagination(items, 2, 10)
    
    assert pagination.page == 2
    assert pagination.per_page == 10
    assert pagination.total_entries == 100
    assert pagination.total_pages == 10
    assert pagination.items_page == items[10:20]
    assert pagination.start_index == 11
    assert pagination.end_index == 20


def test_pagination_empty_items():
    pagination = Pagination([], 1, 10)
    
    assert pagination.page == 1
    assert pagination.per_page == 10
    assert pagination.total_entries == 0
    assert pagination.total_pages == 1
    assert pagination.items_page == []
    assert pagination.start_index == 0
    assert pagination.end_index == 0


def test_pagination_page_out_of_range():
    items = list(range(30))
    
    # Page too high
    pagination = Pagination(items, 10, 10)
    assert pagination.page == 3  # Should be adjusted to max valid page
    assert pagination.items_page == items[20:30]
    
    # Page too low
    pagination = Pagination(items, -1, 10)
    assert pagination.page == 1  # Should be adjusted to min valid page
    assert pagination.items_page == items[0:10]


def test_pagination_has_prev_next():
    items = list(range(100))
    
    # First page
    pagination = Pagination(items, 1, 10)
    assert pagination.has_prev is False
    assert pagination.has_next is True
    assert pagination.prev_page == 1  # Stays at 1
    assert pagination.next_page == 2
    
    # Middle page
    pagination = Pagination(items, 5, 10)
    assert pagination.has_prev is True
    assert pagination.has_next is True
    assert pagination.prev_page == 4
    assert pagination.next_page == 6
    
    # Last page
    pagination = Pagination(items, 10, 10)
    assert pagination.has_prev is True
    assert pagination.has_next is False
    assert pagination.prev_page == 9
    assert pagination.next_page == 10  # Stays at 10


def test_pagination_iter_pages():
    items = list(range(12))
    pagination = Pagination(items, 6, 1)

    middle = pagination.page
    end = pagination.total_pages
    
    def create_expected_pages():
        expected = [
            1, 
            2,
            None,
            middle - 2,
            middle - 1, 
            middle,
            middle + 1, 
            middle + 2,
            None,
            end - 1, 
            end,
        ]
        return expected  # Remove duplicates and sort
    
    expected_pages = create_expected_pages()
    pages = list(pagination.iter_pages())
    
    assert pages == expected_pages


def test_get_pagination_args():
    app = Flask(__name__)
    
    # Test with valid args
    with app.test_request_context('/?page=2&per_page=50'):
        page, per_page = get_pagination_args()
        assert page == 2
        assert per_page == 50
    
    # Test with invalid args
    with app.test_request_context('/?page=abc&per_page=xyz'):
        page, per_page = get_pagination_args()
        assert page == 1  # Default
        assert per_page == 25  # Default
    
    # Test with out-of-range values
    with app.test_request_context('/?page=-1&per_page=500'):
        page, per_page = get_pagination_args()
        assert page == 1  # Minimum
        assert per_page == 100  # Maximum


def test_paginate_function():
    items = list(range(100))
    
    app = Flask(__name__)
    with app.test_request_context('/?page=2&per_page=20'):
        pagination, per_page = paginate(items)
        assert isinstance(pagination, Pagination)
        assert pagination.page == 2
        assert pagination.per_page == 20
        assert per_page == 20
        assert pagination.items_page == items[20:40]
