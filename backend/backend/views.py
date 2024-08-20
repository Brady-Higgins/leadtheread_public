from django.shortcuts import render
from .utils import deep_search_books

import time

def homepage(request):
    return render(request, 'home.html')

def custom_404_view(request,exception):
    return render(request,'404.html', {}, status=404)

def book_search(request):
    query = request.GET.get('book-search')
    fiction_type = request.GET.get('fiction-type')
    if fiction_type == "fiction":
        fic_bool = 1
    else:
        fic_bool = 0
    resp = deep_search_books(query,12,8,fic_bool)
    liked = []
    if request.user.is_authenticated:
        liked_books = request.user.liked_books.all()
        for book in liked_books:
            liked.append(book.isbn)
    return render(request, 'book_search.html', {'results':resp, 'liked_books':liked})