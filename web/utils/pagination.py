from math import ceil
from flask import request
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class Pagination:
    @tracer.start_as_current_span("pagination.Pagination.__init__")
    def __init__(self, items, page, per_page, total_entries=None):
        current_span = trace.get_current_span()
        current_span.set_attribute("pagination.items_len", len(items) if hasattr(items, "__len__") else 0)
        current_span.set_attribute("pagination.page", int(page))
        current_span.set_attribute("pagination.per_page", int(per_page))
        self.items_page = items  # This is now the paginated subset, not all items
        self.page = int(page)
        self.per_page = int(per_page)  # Ensure per_page is an integer
        
        # If total_entries is provided, use it; otherwise calculate from items length (backwards compatibility)
        if total_entries is not None:
            self.total_entries = total_entries
        else:
            self.total_entries = len(items)
        
        self.total_pages = max(1, ceil(self.total_entries / float(self.per_page)))
        current_span.set_attribute("pagination.total_entries", int(self.total_entries))
        current_span.set_attribute("pagination.total_pages", int(self.total_pages))
        
        # Ensure page is within valid range
        self.page = max(1, min(self.page, self.total_pages))
        
        # Calculate display indices based on current page and per_page
        start_index = (self.page - 1) * self.per_page
        end_index = min(start_index + self.per_page, self.total_entries)
        
        # Update display indices
        self.start_index = start_index + 1 if self.total_entries > 0 else 0
        self.end_index = end_index if self.total_entries > 0 else 0

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def prev_page(self):
        return self.page - 1 if self.has_prev else self.page

    @property
    def has_next(self):
        return self.page < self.total_pages

    @property
    def next_page(self):
        return self.page + 1 if self.has_next else self.page

    def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
        last = 0
        for num in range(1, self.total_pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and num < self.page + right_current) or \
               num > self.total_pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num

@tracer.start_as_current_span("pagination.get_pagination_args")
def get_pagination_args():
    """Helper function to get pagination arguments from request"""
    current_span = trace.get_current_span()
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 25))
    except (TypeError, ValueError):
        page = 1
        per_page = 25
    
    # Ensure reasonable limits
    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    current_span.set_attribute("pagination.page", page)
    current_span.set_attribute("pagination.per_page", per_page)
    
    return page, per_page

@tracer.start_as_current_span("pagination.paginate")
def paginate(items, total_entries=None):
    """Helper function to create a pagination object with request args
    
    Args:
        items: The paginated subset of items to display
        total_entries: Total number of entries (if None, will use len(items) for backwards compatibility)
    """
    current_span = trace.get_current_span()
    page, per_page = get_pagination_args()
    pagination = Pagination(items, page, per_page, total_entries)
    current_span.set_attribute("pagination.total_entries", int(pagination.total_entries))
    current_span.set_attribute("pagination.page", pagination.page)
    current_span.set_attribute("pagination.per_page", pagination.per_page)
    current_span.set_attribute("pagination.total_pages", pagination.total_pages)
    return pagination, per_page 