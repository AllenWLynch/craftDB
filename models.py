from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, int_list_validator
from collections import Counter
# Create your models here.

class OreDict(models.Model):
    name = models.CharField(max_length = 200)

    def __str__(self):
        return self.name

class Mod(models.Model):
    name = models.CharField(max_length = 200)

    def __str__(self):
        return self.name

class Item(models.Model):
    display_name = models.CharField('Item Name', max_length = 300)
    itemid = models.CharField('ID',max_length = 300)
    stack = models.IntegerField('Stack Size', default = 64, validators=[MinValueValidator(1), MaxValueValidator(64)])
    
    mod = models.ForeignKey(Mod, on_delete = models.CASCADE, verbose_name = 'Source Mod')
    oredict = models.ManyToManyField(OreDict, blank = True, verbose_name = 'Ore Dictionary')
    base_resource = models.BooleanField('Base Resource', default = False)
    
    def __str__(self):
        return '{} ({})'.format(self.display_name, self.mod.name)

    @staticmethod
    def define_from_infobox(item_info):
        try:
            return Item.objects.get(display_name = item_info['display_name'], mod__name = item_info['mod'])
        except Item.DoesNotExist:
            try:
                in_mod = Mod.objects.get(name = item_info['mod'])
            except Mod.DoesNotExist:
                raise Exception(item_info['display_name'] + ' is not in your modpack')
            else:
                return Item.objects.create(
                    display_name = item_info['display_name'],
                    mod = in_mod,
                    stack = int(item_info['stack']),
                )                

    @staticmethod
    def find_item(display_name, mod):
        if mod == None:
            return Item.objects.get(display_name = display_name)
        else:
            return Item.objects.get(display_name = display_name, mod__name = mod)

class Machine(models.Model):
    name = models.CharField(max_length = 200)
    aliases = models.ManyToManyField('self', blank = True)
    
    def __str__(self):
        return self.name

    def all_possible_machines(self):
        return [self.name, *self.aliases.values_list('name', flat = True)]

class Recipe(models.Model):
    output = models.ForeignKey(Item, on_delete = models.CASCADE, verbose_name = 'Output')
    amount = models.IntegerField('Amount',default=1)
    
    class Meta:
        verbose_name = 'Recipe'
        verbose_name_plural = 'Recipes'
    
    def __str__(self):
        return 'ID {} | {}x {}'.format(str(self.pk), self.amount, str(self.output))


class ByProducts(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete = models.CASCADE)
    item = models.ForeignKey(Item, on_delete = models.CASCADE, verbose_name = 'Byproduct')
    amount = models.IntegerField('Amount',default=1)

    def __str__(self):
        return str(self.amount) + 'x' + str(self.item)

    class Meta:
        verbose_name = 'Byproduct'
        verbose_name_plural = 'Byproducts'


class MachineRecipe(Recipe):
    machine = models.ForeignKey(Machine, on_delete = models.CASCADE, verbose_name = 'Machine')

    def required_resources(self):
        input_counter = Counter()
        for _input in self.machineinput_set.all():
            input_counter[_input.item.itemid] += _input.amount
        return input_counter

class MachineInput(models.Model):
    recipe = models.ForeignKey(MachineRecipe, on_delete = models.CASCADE)
    item = models.ForeignKey(Item, on_delete = models.CASCADE, verbose_name = 'Input')
    amount = models.IntegerField('Amount',default=1)


class CraftingRecipe(Recipe):
    
    def required_resources(self):
        input_counter = Counter()
        for _input in self.slotdata_set.all():
            input_counter[_input.item.itemid] += (len(_input.slots) + 1)/2
        return input_counter

class Slotdata(models.Model):
    recipe = models.ForeignKey(CraftingRecipe,on_delete = models.CASCADE)
    slots = models.CharField('Slots', validators=[int_list_validator], max_length = 100, default = '1')  
    item = models.ForeignKey(Item, on_delete = models.CASCADE, verbose_name = 'Item')
    
    def __str__(self):
        return 'Slots {}: {}'.format(self.slots, str(self.item))

    class Meta:
        verbose_name = 'Slot Data'
        verbose_name_plural = 'Slot Data'
