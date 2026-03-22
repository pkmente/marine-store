from rest_framework import serializers
from .models import Category, Product, ProductImage, Cart, CartItem, Address, Order, OrderItem


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(source='products.count', read_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'image_url', 'product_count']

    def get_image_url(self, obj):
        return obj.image.url if obj.image else ''


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'image_url', 'is_primary']

    def get_image_url(self, obj):
        return obj.image.url if obj.image else ''


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'price', 'discounted_price',
                  'effective_price', 'discount_percent', 'image', 'image_url',
                  'stock', 'category_name', 'is_featured']

    def get_image_url(self, obj):
        return obj.image.url if obj.image else ''


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)
    vendor_name = serializers.CharField(source='vendor.profile.full_name', read_only=True, default='')
    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'description', 'price', 'discounted_price',
                  'effective_price', 'discount_percent', 'image', 'image_url', 'images',
                  'stock', 'category', 'vendor_name', 'is_featured', 'created_at']

    def get_image_url(self, obj):
        return obj.image.url if obj.image else ''


class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['name', 'slug', 'description', 'price', 'discounted_price',
                  'stock', 'image', 'category', 'is_featured']


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True),
        source='product', write_only=True
    )
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'subtotal']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total', 'item_count']


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'full_name', 'phone', 'line1', 'line2',
                  'city', 'state', 'pincode', 'is_default']


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'product_image', 'price', 'quantity', 'subtotal']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    address = AddressSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'status', 'payment_status', 'total_amount', 'items',
                  'address', 'razorpay_order_id', 'notes', 'created_at']
