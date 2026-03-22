from django.contrib import admin
from .models import Category, Product, ProductImage, Cart, CartItem, Address, Order, OrderItem

from django.utils.html import format_html
# @admin.register(Category)
# class CategoryAdmin(admin.ModelAdmin):
#     list_display = ['name', 'slug', 'is_active', 'created_at']
#     prepopulated_fields = {'slug': ('name',)}
#     list_filter = ['is_active']
#     search_fields = ['name']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at', 'image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="60" />', obj.image.url)
        return "No Image"


# class ProductImageInline(admin.TabularInline):
#     model = ProductImage
#     extra = 1


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ['preview']

    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" />', obj.image.url)
        return "No Image"
    

# @admin.register(Product)
# class ProductAdmin(admin.ModelAdmin):
#     list_display = ['name', 'category', 'vendor', 'price', 'discounted_price', 'stock', 'is_active', 'is_featured']
#     list_filter = ['is_active', 'is_featured', 'category']
#     search_fields = ['name', 'description']
#     prepopulated_fields = {'slug': ('name',)}
#     inlines = [ProductImageInline]



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'vendor', 'price',
        'discounted_price', 'stock', 'is_active',
        'is_featured', 'image_preview'   # 👈 add this
    ]
    list_filter = ['is_active', 'is_featured', 'category']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="60" />', obj.image.url)
        return "No Image"
    


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'price', 'quantity', 'subtotal']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'payment_status', 'total_amount', 'created_at']
    list_filter = ['status', 'payment_status']
    search_fields = ['user__phone_number', 'razorpay_order_id']
    inlines = [OrderItemInline]
    readonly_fields = ['razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature']


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'user', 'city', 'state', 'pincode', 'is_default']
    search_fields = ['full_name', 'user__phone_number', 'city']