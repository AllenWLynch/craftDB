from django.urls import path
from . import views

app_name = 'craftDB'
urlpatterns = [
    path('', views.index, name='index'),
    path('testview', views.testview, name = 'testview'),
    #path('addrecipe',views.addRecipeForm, name = 'addRecipeForm'),
    #path('scrapedata',views.scrapeData, name = 'scrapedata'),
    #path('saverecipes',views.saveRecipes, name = 'saverecipes')
]