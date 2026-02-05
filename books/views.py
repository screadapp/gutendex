from django.db.models import Q
from django.core.cache import cache
from django.conf import settings
import hashlib

from rest_framework import exceptions as drf_exceptions, viewsets
from rest_framework.response import Response

from .models import *
from .serializers import *


def get_cache_key(request):
    """Generate a unique cache key based on query parameters."""
    params = sorted(request.GET.items())
    param_string = '&'.join(f'{k}={v}' for k, v in params)
    hash_key = hashlib.md5(param_string.encode()).hexdigest()
    return f'books_list_{hash_key}'


class BookViewSet(viewsets.ModelViewSet):
    """ This is an API endpoint that allows books to be viewed. """

    lookup_field = 'gutenberg_id'

    queryset = Book.objects.exclude(download_count__isnull=True)
    queryset = queryset.exclude(title__isnull=True)

    serializer_class = BookSerializer

    def list(self, request, *args, **kwargs):
        """Override list to add caching."""
        cache_key = get_cache_key(request)
        
        # Try to get from cache
        cached_response = cache.get(cache_key)
        if cached_response is not None:
            return Response(cached_response)
        
        # Get fresh data
        response = super().list(request, *args, **kwargs)
        
        # Cache the response data for 1 hour
        cache_timeout = getattr(settings, 'BOOK_CACHE_TIMEOUT', 3600)
        cache.set(cache_key, response.data, cache_timeout)
        
        return response

    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to add caching for individual books."""
        book_id = kwargs.get('gutenberg_id')
        cache_key = f'book_{book_id}'
        
        # Try to get from cache
        cached_response = cache.get(cache_key)
        if cached_response is not None:
            return Response(cached_response)
        
        # Get fresh data
        response = super().retrieve(request, *args, **kwargs)
        
        # Cache for 24 hours since individual books rarely change
        cache.set(cache_key, response.data, 86400)
        
        return response

    def get_queryset(self):
        queryset = self.queryset

        sort = self.request.GET.get('sort')
        if sort == 'ascending':
            queryset = queryset.order_by('id')
        elif sort == 'descending':
            queryset = queryset.order_by('-id')
        else:
            queryset = queryset.order_by('-download_count')

        author_year_end = self.request.GET.get('author_year_end')
        try:
            author_year_end = int(author_year_end)
        except:
            author_year_end = None
        if author_year_end is not None:
            queryset = queryset.filter(
                Q(authors__birth_year__lte=author_year_end) |
                Q(authors__death_year__lte=author_year_end)
            )

        author_year_start = self.request.GET.get('author_year_start')
        try:
            author_year_start = int(author_year_start)
        except:
            author_year_start = None
        if author_year_start is not None:
            queryset = queryset.filter(
                Q(authors__birth_year__gte=author_year_start) |
                Q(authors__death_year__gte=author_year_start)
            )

        copyright_parameter = self.request.GET.get('copyright')
        if copyright_parameter is not None:
            copyright_strings = copyright_parameter.split(',')
            copyright_values = set()
            for copyright_string in copyright_strings:
                if copyright_string == 'true':
                    copyright_values.add(True)
                elif copyright_string == 'false':
                    copyright_values.add(False)
                elif copyright_string == 'null':
                    copyright_values.add(None)
            for value in [True, False, None]:
                if value not in copyright_values:
                    queryset = queryset.exclude(copyright=value)

        id_string = self.request.GET.get('ids')
        if id_string is not None:
            ids = id_string.split(',')

            try:
                ids = [int(id) for id in ids]
            except ValueError:
                pass
            else:
                queryset = queryset.filter(gutenberg_id__in=ids)

        language_string = self.request.GET.get('languages')
        if language_string is not None:
            language_codes = [code.lower() for code in language_string.split(',')]
            queryset = queryset.filter(languages__code__in=language_codes)

        mime_type = self.request.GET.get('mime_type')
        if mime_type is not None:
            queryset = queryset.filter(format__mime_type__startswith=mime_type)

        search_string = self.request.GET.get('search')
        if search_string is not None:
            search_terms = search_string.split(' ')
            for term in search_terms[:32]:
                queryset = queryset.filter(
                    Q(authors__name__icontains=term) | Q(title__icontains=term)
                )

        topic = self.request.GET.get('topic')
        if topic is not None:
            queryset = queryset.filter(
                Q(bookshelves__name__icontains=topic) | Q(subjects__name__icontains=topic)
            )

        return queryset.distinct()
