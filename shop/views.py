import hmac
import hashlib
import logging

import razorpay
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.models import Profile
from .models import Category, Product, Cart, CartItem, Address, Order, OrderItem
from .serializers import (
    CategorySerializer, ProductListSerializer, ProductDetailSerializer,
    ProductCreateSerializer, CartSerializer, CartItemSerializer,
    AddressSerializer, OrderSerializer,
)

logger = logging.getLogger(__name__)


def is_vendor_or_admin(user):
    try:
        return user.profile.role in ('vendor', 'admin')
    except Exception:
        return False


def is_admin(user):
    try:
        return user.profile.role == 'admin'
    except Exception:
        return False


# ── Categories ────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def category_list(request):
    cats = Category.objects.filter(is_active=True)
    list_cats = [CategorySerializer(cat, context={'request': request}).data for cat in cats]
    print("============================================",list_cats)
    return Response(CategorySerializer(cats, many=True, context={'request': request}).data)


# ── Products ──────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def product_list(request):
    qs = Product.objects.filter(is_active=True).select_related('category')
    category = request.query_params.get('category')
    search = request.query_params.get('search')
    featured = request.query_params.get('featured')

    if category:
        qs = qs.filter(category__slug=category)
    if search:
        qs = qs.filter(name__icontains=search)
    if featured == 'true':
        qs = qs.filter(is_featured=True)

    return Response(ProductListSerializer(qs, many=True, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    return Response(ProductDetailSerializer(product, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def product_create(request):
    if not is_vendor_or_admin(request.user):
        return Response({'error': 'Only vendors and admins can create products.'}, status=status.HTTP_403_FORBIDDEN)
    serializer = ProductCreateSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(vendor=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def product_manage(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if product.vendor != request.user and not is_admin(request.user):
        return Response({'error': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        serializer = ProductCreateSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'DELETE':
        product.is_active = False
        product.save()
        return Response({'message': 'Product deactivated.'})


# ── Cart ──────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cart_detail(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return Response(CartSerializer(cart, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cart_add(request):
    product_id = request.data.get('product_id')
    quantity = int(request.data.get('quantity', 1))

    product = get_object_or_404(Product, pk=product_id, is_active=True)
    if product.stock < quantity:
        return Response({'error': 'Insufficient stock.'}, status=status.HTTP_400_BAD_REQUEST)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        item.quantity += quantity
    else:
        item.quantity = quantity
    item.save()

    return Response(CartSerializer(cart, context={'request': request}).data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def cart_update(request, item_id):
    cart = get_object_or_404(Cart, user=request.user)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    quantity = int(request.data.get('quantity', 1))

    if quantity <= 0:
        item.delete()
    else:
        if item.product.stock < quantity:
            return Response({'error': 'Insufficient stock.'}, status=status.HTTP_400_BAD_REQUEST)
        item.quantity = quantity
        item.save()

    return Response(CartSerializer(cart, context={'request': request}).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cart_remove(request, item_id):
    cart = get_object_or_404(Cart, user=request.user)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    item.delete()
    return Response(CartSerializer(cart, context={'request': request}).data)


# ── Addresses ─────────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def address_list_create(request):
    if request.method == 'GET':
        addresses = Address.objects.filter(user=request.user)
        return Response(AddressSerializer(addresses, many=True).data)

    serializer = AddressSerializer(data=request.data)
    if serializer.is_valid():
        if serializer.validated_data.get('is_default'):
            Address.objects.filter(user=request.user).update(is_default=False)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def address_manage(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)

    if request.method == 'PUT':
        serializer = AddressSerializer(address, data=request.data, partial=True)
        if serializer.is_valid():
            if serializer.validated_data.get('is_default'):
                Address.objects.filter(user=request.user).update(is_default=False)
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    address.delete()
    return Response({'message': 'Address deleted.'})


# ── Orders & Razorpay ─────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    address_id = request.data.get('address_id')
    notes = request.data.get('notes', '')

    address = get_object_or_404(Address, pk=address_id, user=request.user)
    cart = get_object_or_404(Cart, user=request.user)

    if not cart.items.exists():
        return Response({'error': 'Cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

    # Validate stock
    for item in cart.items.all():
        if item.product.stock < item.quantity:
            return Response(
                {'error': f'Insufficient stock for {item.product.name}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    total = float(cart.total)

    # Create Razorpay order
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        rzp_order = client.order.create({
            'amount': int(total * 100),  # paise
            'currency': 'INR',
            'payment_capture': 1,
        })
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}")
        return Response({'error': 'Payment gateway error. Try again.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    # Create DB order
    order = Order.objects.create(
        user=request.user,
        address=address,
        total_amount=total,
        razorpay_order_id=rzp_order['id'],
        notes=notes,
    )

    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            product_name=item.product.name,
            product_image=item.product.image.url if item.product.image else '',
            price=item.product.effective_price,
            quantity=item.quantity,
        )
        # Deduct stock
        item.product.stock -= item.quantity
        item.product.save()

    # Clear cart
    cart.items.all().delete()

    return Response({
        'order_id': order.id,
        'razorpay_order_id': rzp_order['id'],
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'amount': int(total * 100),
        'currency': 'INR',
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    razorpay_order_id = request.data.get('razorpay_order_id')
    razorpay_payment_id = request.data.get('razorpay_payment_id')
    razorpay_signature = request.data.get('razorpay_signature')

    order = get_object_or_404(Order, razorpay_order_id=razorpay_order_id, user=request.user)

    # Verify signature
    body = f"{razorpay_order_id}|{razorpay_payment_id}"
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        body.encode(),
        hashlib.sha256
    ).hexdigest()

    if expected == razorpay_signature:
        order.payment_status = 'paid'
        order.status = 'confirmed'
        order.razorpay_payment_id = razorpay_payment_id
        order.razorpay_signature = razorpay_signature
        order.save()
        return Response({'message': 'Payment verified. Order confirmed!'})
    else:
        order.payment_status = 'failed'
        order.save()
        return Response({'error': 'Payment verification failed.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_list(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items', 'address')
    return Response(OrderSerializer(orders, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return Response(OrderSerializer(order).data)


# ── Vendor: my products ───────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vendor_products(request):
    if not is_vendor_or_admin(request.user):
        return Response({'error': 'Vendors only.'}, status=status.HTTP_403_FORBIDDEN)
    products = Product.objects.filter(vendor=request.user)
    return Response(ProductListSerializer(products, many=True, context={'request': request}).data)


# ── Admin: all orders ─────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_orders(request):
    if not is_admin(request.user):
        return Response({'error': 'Admins only.'}, status=status.HTTP_403_FORBIDDEN)
    orders = Order.objects.all().select_related('user', 'address').prefetch_related('items')
    return Response(OrderSerializer(orders, many=True).data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def admin_update_order_status(request, pk):
    if not is_admin(request.user):
        return Response({'error': 'Admins only.'}, status=status.HTTP_403_FORBIDDEN)
    order = get_object_or_404(Order, pk=pk)
    new_status = request.data.get('status')
    if new_status not in dict(Order.STATUS_CHOICES):
        return Response({'error': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)
    order.status = new_status
    order.save()
    return Response({'message': f'Order status updated to {new_status}.'})