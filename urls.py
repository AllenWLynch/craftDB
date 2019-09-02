from django.urls import path
from . import views

app_name = 'craftDB'
urlpatterns = [
    path('', views.index, name='index'),
    path('testview/', views.testview, name = 'testview'),
    path('items/', views.get_item_names, name= 'items'),
    path('recipe/<int:id>', views.get_recipe_info, name='recipe')
]