from django.contrib import admin
from craftDB.models import *
from django import forms


class RecipeAdmin(admin.ModelAdmin):
    fieldsets = [
        ('OUTPUT', { 'fields' : ['output','amount',]}),
    ]
    list_display = ('id','output','amount')
    autocomplete_fields = ['output']

class SlotdataInLine(admin.TabularInline):
    model = Slotdata
    extra = 0
    autocomplete_fields = ['item']

class CraftingRecipeAdmin(RecipeAdmin):
    inlines = [SlotdataInLine]

class MachineInputInLine(admin.TabularInline):
    model = MachineInput
    extra = 0
    autocomplete_fields = ['item']

class MachineRecipeAdmin(RecipeAdmin):
    inlines = [MachineInputInLine]
    
class ItemAdmin(admin.ModelAdmin):
    search_fields = ['display_name']
    autocomplete_fields = ['mod']

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

admin.site.register(Item, ItemAdmin)
admin.site.register(Machine, MachineAdmin)
admin.site.register(Mod, ModAdmin)
admin.site.register(OreDict)
admin.site.register(ModPack)
admin.site.register(Group)
admin.site.register(CraftingRecipe, CraftingRecipeAdmin)
admin.site.register(MachineRecipe, MachineRecipeAdmin)
