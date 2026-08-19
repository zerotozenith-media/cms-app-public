"""
Standard pagination for all API list endpoints. The default DRF
PageNumberPagination doesn't allow client-controlled page size unless
page_size_query_param is explicitly set , found this while building the
Batch 3.4 frontend, where the Members list needed a page size (8,
matching the demo) different from the backend's general default (25).
Fixed globally here rather than worked around in one page, since every
future frontend list screen will have the same need.
"""
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 100
