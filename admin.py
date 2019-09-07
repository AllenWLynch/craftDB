from django.contrib import admin
from craftDB.models import *
from django import forms
from django.contrib.admin import AdminSite
from craftDB.views import addRecipeForm, scrapeData, saveRecipes, disambiguation, index
from django.urls import path, reverse
from  django.contrib.contenttypes.admin import GenericTabularInline

class MyAdminSite(AdminSite):
    site_header = 'craftDB Administration'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('addrecipe', self.admin_view(addRecipeForm), name = 'addrecipe'),
            path('disambiguation', self.admin_view(disambiguation), name = 'disambiguation'),
            path('scrapedata',self.admin_view(scrapeData), name = 'scrapedata'),
            path('saverecipes',self.admin_view(saveRecipes), name = 'saverecipes'),
        ]
        return urls + my_urls

myadmin = MyAdminSite(name = 'craftadmin')
myadmin.site_url = '/craftDB'

class RecipeAdmin(admin.ModelAdmin):
    fieldsets = [
        ('OUTPUT', { 'fields' : ['output','amount',]}),
    ]
    list_display = ('id','output','amount')
    autocomplete_fields = ['output']

class SlotdataInLine(admin.TabularInline):
    model = Slotdata
    extra = 0

class CraftingRecipeAdmin(RecipeAdmin):
    #inlines = [SlotdataInLine]
    pass

class MachineInputInLine(admin.TabularInline):
    model = MachineInput
    extra = 0
    #autocomplete_fields = ['item']

class MachineRecipeAdmin(admin.ModelAdmin):
    fieldsets = [
        ('OUTPUT', { 'fields' : ['output','amount',]}),
        ('MACHINING', {'fields' : ['machine']}),
    ]
    list_display = ('id','output','amount')
    autocomplete_fields = ['output','machine']
    inlines = [MachineInputInLine]
    
class ItemAdmin(admin.ModelAdmin):
    search_fields = ['display_name']
    autocomplete_fields = ['mod']
    list_display = ('display_name', 'mod','sprite')

class ModAdmin(admin.ModelAdmin):
    search_fields = ['name']

class MachineInline(admin.TabularInline):
    model = Machine.aliases.through
    fk_name = 'to_machine'
    extra = 0

class MachineAdmin(admin.ModelAdmin):
    inlines = [MachineInline]
    exclude = ('aliases',)
    search_fields = ['name']

myadmin.register(Item, ItemAdmin)
myadmin.register(Machine, MachineAdmin)
myadmin.register(Mod, ModAdmin)
myadmin.register(OreDict)
myadmin.register(ModPack)
myadmin.register(Group)
myadmin.register(CraftingRecipe, CraftingRecipeAdmin)
myadmin.register(MachineRecipe, MachineRecipeAdmin)
