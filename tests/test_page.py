import pytest
from flask import Flask
from web.backend.services.pagination import Pagination, get_pagination_args, paginate


def test_pagination_init():
    items = list(range(10, 20))  # This represents page 2 of data (items 10-19)
    pagination = Pagination(items, 2, 10, total_entries=100)
    
    assert pagination.page == 2
    assert pagination.per_page == 10
    assert pagination.total_entries == 100
    assert pagination.total_pages == 10
    assert pagination.items_page == items  # Should be the pre-paginated subset
    assert pagination.start_index == 11
    assert pagination.end_index == 20


def test_pagination_init_backwards_compatibility():
    """Test that old behavior still works when total_entries is not provided"""
    items = list(range(100))
    pagination = Pagination(items, 2, 10)
    
    assert pagination.page == 2
    assert pagination.per_page == 10
    assert pagination.total_entries == 100
    assert pagination.total_pages == 10
    assert pagination.items_page == items  # Full dataset when total_entries not provided
    assert pagination.start_index == 11
    assert pagination.end_index == 20


def test_pagination_empty_items():
    pagination = Pagination([], 1, 10, total_entries=0)
    
    assert pagination.page == 1
    assert pagination.per_page == 10
    assert pagination.total_entries == 0
    assert pagination.total_pages == 1
    assert pagination.items_page == []
    assert pagination.start_index == 0
    assert pagination.end_index == 0


def test_pagination_page_out_of_range():
    # Test with new approach - items represent the actual page data
    items_page_3 = list(range(20, 30))  # Items for page 3 (last page)
    
    # Page too high - should be adjusted to max valid page (3)
    pagination = Pagination(items_page_3, 10, 10, total_entries=30)
    assert pagination.page == 3  # Should be adjusted to max valid page
    assert pagination.items_page == items_page_3
    
    # Page too low - should be adjusted to min valid page (1)
    items_page_1 = list(range(0, 10))  # Items for page 1
    pagination = Pagination(items_page_1, -1, 10, total_entries=30)
    assert pagination.page == 1  # Should be adjusted to min valid page
    assert pagination.items_page == items_page_1


def test_pagination_string_parameters():
    items = list(range(10, 20))  # Page 2 data
    pagination = Pagination(items, "2", "10", total_entries=100)
    
    assert pagination.page == 2
    assert pagination.per_page == 10
    assert pagination.total_entries == 100
    assert pagination.total_pages == 10
    assert pagination.items_page == items


def test_pagination_invalid_parameters():
    """Test that invalid parameters raise appropriate exceptions"""
    items = list(range(10))
    
    # Non-convertible string should raise ValueError
    with pytest.raises(ValueError):
        Pagination(items, "abc", 10, total_entries=100)
    
    with pytest.raises(ValueError):
        Pagination(items, 1, "xyz", total_entries=100)
    
    # None values should raise TypeError
    with pytest.raises(TypeError):
        Pagination(items, None, 10, total_entries=100)
    
    with pytest.raises(TypeError):
        Pagination(items, 1, None, total_entries=100)


def test_pagination_has_prev_next():
    # Test with new approach using total_entries
    
    # First page
    items_page_1 = list(range(0, 10))
    pagination = Pagination(items_page_1, 1, 10, total_entries=100)
    assert pagination.has_prev is False
    assert pagination.has_next is True
    assert pagination.prev_page == 1  # Stays at 1
    assert pagination.next_page == 2
    
    # Middle page
    items_page_5 = list(range(40, 50))
    pagination = Pagination(items_page_5, 5, 10, total_entries=100)
    assert pagination.has_prev is True
    assert pagination.has_next is True
    assert pagination.prev_page == 4
    assert pagination.next_page == 6
    
    # Last page
    items_page_10 = list(range(90, 100))
    pagination = Pagination(items_page_10, 10, 10, total_entries=100)
    assert pagination.has_prev is True
    assert pagination.has_next is False
    assert pagination.prev_page == 9
    assert pagination.next_page == 10  # Stays at 10


def test_pagination_iter_pages():
    items = list(range(5, 6))  # Page 6 data (1 item per page)
    pagination = Pagination(items, 6, 1, total_entries=12)

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
        return expected
    
    expected_pages = create_expected_pages()
    pages = list(pagination.iter_pages())
    
    assert pages == expected_pages


def test_pagination_iter_pages_custom_params():
    items = list(range(49, 50))  # Page 50 data (1 item per page)
    pagination = Pagination(items, 50, 1, total_entries=100)
    
    # Custom parameters: show only 1 page on each edge and 1 page around current
    pages = list(pagination.iter_pages(left_edge=1, left_current=1, right_current=1, right_edge=1))
    
    # Check structure without hardcoding exact indices
    assert len(pages) > 0
    assert pages[0] == 1  # First page should always be 1
    
    # Check that there's a None (gap) in the list
    assert None in pages
    
    # Check that current page is in the list
    assert 50 in pages
    
    # Check that last page is in the list
    assert 100 in pages
    
    # Check that we have pages around current page
    current_index = pages.index(50)
    if current_index > 0 and current_index < len(pages) - 1:
        # If current page is not at the edges, check surrounding pages
        if pages[current_index - 1] is not None:
            assert pages[current_index - 1] == 49
        if pages[current_index + 1] is not None:
            assert pages[current_index + 1] == 51


def test_pagination_iter_pages_few_pages():
    """Test iter_pages when there are few pages (no gaps)"""
    items = list(range(10, 20))  # Page 2 data
    pagination = Pagination(items, 2, 10, total_entries=30)
    
    # With only 3 pages, there should be no gaps
    pages = list(pagination.iter_pages())
    assert pages == [1, 2, 3]
    assert None not in pages
    
    # With custom parameters that would normally create gaps
    pages = list(pagination.iter_pages(left_edge=1, left_current=1, right_current=1, right_edge=1))
    assert pages == [1, 2, 3]
    assert None not in pages


def test_pagination_single_page():
    items = list(range(5))  # All items fit on one page
    pagination = Pagination(items, 1, 10, total_entries=5)
    
    assert pagination.page == 1
    assert pagination.per_page == 10
    assert pagination.total_entries == 5
    assert pagination.total_pages == 1
    assert pagination.items_page == items
    assert pagination.has_prev is False
    assert pagination.has_next is False
    assert pagination.prev_page == 1
    assert pagination.next_page == 1
    
    # Test iter_pages with single page
    pages = list(pagination.iter_pages())
    assert pages == [1]


def test_pagination_small_per_page():
    """Test pagination with very small per_page value (1)"""
    items = [4]  # Page 5 data (1 item per page, zero-indexed item 4)
    pagination = Pagination(items, 5, 1, total_entries=10)
    
    assert pagination.page == 5
    assert pagination.per_page == 1
    assert pagination.total_entries == 10
    assert pagination.total_pages == 10
    assert pagination.items_page == [4]
    assert pagination.start_index == 5
    assert pagination.end_index == 5
    assert pagination.has_prev is True
    assert pagination.has_next is True
    assert pagination.prev_page == 4
    assert pagination.next_page == 6


def test_pagination_large_dataset():
    """Test pagination with a large number of items"""
    # Page 1000 data (100 items)
    items = list(range(99900, 100000))
    pagination = Pagination(items, 1000, 100, total_entries=100000)
    
    assert pagination.page == 1000
    assert pagination.per_page == 100
    assert pagination.total_entries == 100000
    assert pagination.total_pages == 1000
    assert len(pagination.items_page) == 100
    assert pagination.items_page[0] == 99900  # First item on page 1000
    assert pagination.items_page[-1] == 99999  # Last item
    assert pagination.start_index == 99901  # 1-indexed for display
    assert pagination.end_index == 100000
    assert pagination.has_prev is True
    assert pagination.has_next is False


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
        
    # Test with missing args
    with app.test_request_context('/'):
        page, per_page = get_pagination_args()
        assert page == 1  # Default
        assert per_page == 25  # Default


def test_paginate_function():
    items = list(range(20, 40))  # Page 2 data
    
    app = Flask(__name__)
    with app.test_request_context('/?page=2&per_page=20'):
        pagination, per_page = paginate(items, total_entries=100)
        assert isinstance(pagination, Pagination)
        assert pagination.page == 2
        assert pagination.per_page == 20
        assert per_page == 20
        assert pagination.items_page == items
        assert pagination.total_entries == 100


def test_paginate_function_backwards_compatibility():
    """Test that paginate still works without total_entries for backwards compatibility"""
    items = list(range(100))
    
    app = Flask(__name__)
    with app.test_request_context('/?page=2&per_page=20'):
        pagination, per_page = paginate(items)
        assert isinstance(pagination, Pagination)
        assert pagination.page == 2
        assert pagination.per_page == 20
        assert per_page == 20
        assert pagination.items_page == items
        assert pagination.total_entries == 100  # Should use len(items)


def test_paginate_function_empty_items():
    items = []
    
    app = Flask(__name__)
    with app.test_request_context('/?page=1&per_page=10'):
        pagination, per_page = paginate(items, total_entries=0)
        assert isinstance(pagination, Pagination)
        assert pagination.page == 1
        assert pagination.per_page == 10
        assert per_page == 10
        assert pagination.items_page == []
        assert pagination.total_entries == 0
        assert pagination.total_pages == 1
        assert pagination.has_prev is False
        assert pagination.has_next is False
