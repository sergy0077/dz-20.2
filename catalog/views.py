from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden, HttpResponseRedirect, Http404
from django.urls import reverse_lazy
from django.views.decorators.cache import cache_page
from django.views.generic import ListView, CreateView
from django.views.generic.edit import DeleteView
from blog.models import Blog
from .forms import ProductForm
from .models import Product, Version, Category
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic.detail import DetailView

from .services import get_categories


class CategoryListView(ListView):
    """Контроллер для отображения списка категорий продуктов"""
    extra_context = {
        'title': 'Категории товаров'
    }

    def get_queryset(self):
        # Используем нашу сервисную функцию для получения категорий
        return get_categories()


class CategoryDetailView(DetailView):
    """Контроллер для отображения карточки категории продукта"""
    template_name = 'catalog/category_detail.html'
    context_object_name = 'category'

    def get_object(self):
        category_id = self.kwargs['pk']
        categories = get_categories()

        # Ищем категорию с нужным id в списке категорий
        for category in categories:
            if category.id == category_id:
                return category

        # Если категория не найдена, вернем 404
        raise Http404("Категория не найдена")


class IndexView(View):
    """Контроллер для отображения списка всех продуктов"""
    model = Product
    template_name = 'catalog/index.html'

    def get(self, request):
        products = Product.objects.all()

        for product in products:
            active_version = product.version_set.filter(is_active=True).first()
            if active_version:
                product.active_version_number = active_version.version_number
                product.active_version_name = active_version.version_name
            else:
                product.active_version_number = None
                product.active_version_name = None

        return render(request, self.template_name, {'products': products})


class ProductDetailView(View):
    """Контроллер для отображения карточки продукта."""
    model = Product
    template_name = 'catalog/product_detail.html'

    @cache_page(60 * 15)  # Кешировать страницу на 15 минут
    def get(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        return render(request, self.template_name, {'product': product})

    def get_context_data(self, *args, **kwargs):
        context_data = super().get_context_data(*args, **kwargs)
        product = get_object_or_404(Product, pk=self.kwargs['product_id'])
        context_data['title'] = f'Товар из категории: {product.category}'

        active_version = Version.objects.filter(product=self.object, is_active=True).last()
        if active_version:
            context_data['active_version_number'] = active_version.number
            context_data['active_version_name'] = active_version.name
        else:
            context_data['active_version_number'] = None
            context_data['active_version_name'] = None

        return context_data


class ProductCreateView(LoginRequiredMixin, CreateView):
    """Контроллер для создания новых продуктов пользователем."""
    model = Product
    form_class = ProductForm
    success_url = reverse_lazy('catalog:index')
    template_name = 'catalog/product_form.html'
    extra_context = {
        'title': 'Добавить новый продукт:'
    }

    def form_valid(self, form):
        """Контроллер для валидации запрещенных слов"""
        form.instance.clean()  # Вызов валидации перед сохранением
        product = form.save(commit=False)
        """Привязка продукта к авторизованному пользователю"""
        product.owner = self.request.user
        product.save()
        # вызываем метод form_valid класса-родителя, чтобы создать объект Product
        response = super().form_valid(form)

        # Создание новой версии
        version_number = form.cleaned_data['version_number']
        version_name = form.cleaned_data['version_name']
        is_active = form.cleaned_data['is_active']

        version = Version(
            product=form.instance,
            version_number=version_number,
            version_name=version_name,
            is_active=is_active
        )
        version.save()

        form.instance.active_version = version_name  # Установка активной версии
        self.object.active_versions.set(form.cleaned_data['active_versions'])
        return response


class ProductUpdateView(LoginRequiredMixin, View):
    """Контроллер редактирования продуктов с модерацией на владельца"""
    template_name = 'catalog/product_edit_form.html'
    login_url = 'users:login'

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        if request.user != product.owner and not request.user.is_staff:
            return HttpResponseForbidden("Доступ запрещен")
        form = ProductForm(instance=product)
        return render(request, self.template_name, {'product': product, 'form': form})

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        if request.user != product.owner and not request.user.is_staff:
            return HttpResponseForbidden("Доступ запрещен")
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('catalog:index')
        return render(request, self.template_name, {'product': product, 'form': form})


class ProductDeleteView(DeleteView):
    """Контроллер для удаления продукта"""
    model = Product
    template_name = 'catalog/product_confirm_delete.html'
    success_url = reverse_lazy('catalog:index')
    extra_context = {
        'title': 'Удаление записи:'
    }

    def post(self, request, *args, **kwargs):
        # Получаем объект Product, который мы хотим удалить
        product = self.get_object()

        # Удаляем связанные Version перед удалением Product
        versions = Version.objects.filter(product=product)
        versions.delete()

        # Удаляем Product
        product.delete()

        return HttpResponseRedirect(self.success_url)

#########################################################################
@login_required
def contacts(request):
    """Контроллер для отображения контактной информации."""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        print(f'{name} ({email}): {message}')
    return render(request, 'catalog/contacts.html')


#########################################################################
@login_required
def blog_list_view(request):
    """Контроллер для отображения блоговой информации."""
    blogs = Blog.objects.all()
    return render(request, 'blog/list.html', {'blogs': blogs})


##########################################################################
