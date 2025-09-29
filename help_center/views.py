# help_center/views.py
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import HelpCategory, HelpArticle, FAQ

def help_center(request):
    categories = HelpCategory.objects.all()
    featured_articles = HelpArticle.objects.filter(is_featured=True)
    context = {
        'categories': categories,
        'featured_articles': featured_articles,
    }
    return render(request, 'help_center/help_center.html', context)

def category_detail(request, category_id):
    category = get_object_or_404(HelpCategory, id=category_id)
    articles = category.articles.all()
    context = {
        'category': category,
        'articles': articles,
    }
    return render(request, 'help_center/category_detail.html', context)

def article_detail(request, slug):
    article = get_object_or_404(HelpArticle, slug=slug)
    # Incrementar contador de vistas
    article.view_count += 1
    article.save()
    
    context = {
        'article': article,
        'related_articles': article.related_articles.all(),
    }
    return render(request, 'help_center/article_detail.html', context)

def search_help(request):
    query = request.GET.get('q', '')
    results = HelpArticle.objects.filter(
        Q(title__icontains=query) | 
        Q(content__icontains=query)
    ) if query else []
    
    context = {
        'query': query,
        'results': results,
    }
    return render(request, 'help_center/search_results.html', context)

def faq_list(request):
    faqs = FAQ.objects.all()
    context = {
        'faqs': faqs,
    }
    return render(request, 'help_center/faq.html', context)