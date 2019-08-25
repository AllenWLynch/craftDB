from django.contrib import admin
from craftDB.models import *
from django import forms


class RecipeAdmin(admin.ModelAdmin):
    fieldsets = [
        ('OUTPUT', { 'fields' : ['output','amount',]}),
    ]
    list_display = ('id','output','amount')
    autocomplete_fields = ['output']


def slotdata_validation(slot_str):
    component_slots = slot_str.split(',')
    if len(component_slots) > 9:
        return False
    for slot in component_slots:
        if not slot in ['1','2','3','4','5','6','7','8','9','*']:
            return False
    return True

class SlotdataForm(forms.ModelForm):
    class Meta:
        model = Slotdata
        fields = '__all__'

    def clean(self):
        if not slotdata_validation(self.cleaned_data.get('slots')):
            raise forms.ValidationError('Slot field must be comma-delinated list containing Ints 1-9 like: \"1,2,4,9", or \"*\" for all slots.')     
        return self.cleaned_data

class SlotdataInLine(admin.TabularInline):
    model = Slotdata
    form = SlotdataForm
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
admin.site.register(CraftingRecipe, CraftingRecipeAdmin)
admin.site.register(MachineRecipe, MachineRecipeAdmin)
admin.site.register(Mod, ModAdmin)
admin.site.register(OreDict)

# Register your models here.
