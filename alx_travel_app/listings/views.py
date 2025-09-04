
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

import requests

from .models import Listing, Booking, Payments
from .serializers import ListingSerializer, BookingSerializer

CHAPA_URL = "https://api.chapa.co/v1/transaction/initialize"
CHAPA_VERIFY_URL = "https://api.chapa.co/v1/transaction/verify/"


class ListingViewSet(viewsets.ModelViewSet):
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save(user=request.user)

        try:
            # Initiate payment with Chapa
            checkout_url, tx_ref = initiate_payment(
            amount=booking.total_price,
            booking_reference=booking.booking_id,
            user_email=request.user.email,
            first_name=request.user.first_name,
            last_name=request.user.last_name
        )

            # Save payment info
            Payments.objects.create(
                user=request.user,
                booking_reference=booking.booking_id,
                amount=booking.total_price,
                transaction_id=tx_ref,
                status="Pending"
            )

            # Return response
            return Response({
                "status": "success",
                "booking_id": booking.booking_id,
                "checkout_url": checkout_url
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                "status": "failed",
                "message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        


def initiate_payment(amount, booking_reference, user_email, first_name="Guest", last_name="User"):
    headers = {
        "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "amount": str(amount),
        "currency": "ETB",
        "email": user_email,
        "tx_ref": str(booking_reference),  # required
        "callback_url": "http://127.0.0.1:8000/api/verify-payment/",
        "return_url": "http://127.0.0.1:8000/payment-success/",
        "first_name": first_name,
        "last_name": last_name,
        "customization": {
            "title": "ALX Travel",  # max 16 chars
            "description": "Booking payment"
        }
    }

    response = requests.post(CHAPA_URL, headers=headers, json=payload)
    data = response.json()

    # Always check if 'data' exists and has 'checkout_url'
    if data.get("status") == "success" and "data" in data and "checkout_url" in data["data"]:
        checkout_url = data["data"]["checkout_url"]
        tx_ref = data["data"].get("tx_ref") or str(booking_reference)  # fallback
        return checkout_url, tx_ref
    else:
        raise Exception(f"Payment initiation failed: {data}")


@csrf_exempt
def verify_payment(request):
    """
    Verify Chapa payment and update Payments + Booking status
    """
    if request.method != "GET":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    tx_ref = request.GET.get("tx_ref")
    if not tx_ref:
        return JsonResponse({"error": "Missing tx_ref"}, status=400)

    headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}
    response = requests.get(f"{CHAPA_VERIFY_URL}{tx_ref}", headers=headers)
    data = response.json()

    try:
        payment = Payments.objects.get(transaction_id=tx_ref)
    except Payments.DoesNotExist:
        return JsonResponse({"error": "Payment not found"}, status=404)

    if data.get("status") == "success" and data["data"]["status"] == "success":
        payment.status = "Completed"
        payment.save()

        booking = get_object_or_404(Booking, booking_id=payment.booking_reference)
        booking.status = "confirmed"
        booking.save()

        # Optionally trigger Celery task to send email
        # send_booking_confirmation_email.delay(
        #     payment.user.email,
        #     booking.booking_id,
        #     payment.user.first_name,
        #     booking.property.title if booking.property else None,
        #     booking.start_date,
        #     booking.end_date
        # )

        return JsonResponse({"status": "success", "message": "Payment verified, booking confirmed"})
    else:
        payment.status = "Failed"
        payment.save()
        return JsonResponse({"status": "failed", "message": "Payment verification failed"})





# from django.shortcuts import render
# from rest_framework import viewsets
# from .models import Listing, Booking
# from .serializers import ListingSerializer, BookingSerializer
# from rest_framework.permissions import IsAuthenticatedOrReadOnly
# #from .services.chapa import initiate_payment_chapa


# class ListingViewSet(viewsets.ModelViewSet):
#     queryset = Listing.objects.all()
#     serializer_class = ListingSerializer
#     permission_classes = [IsAuthenticatedOrReadOnly]

# # class BookingViewSet(viewsets.ModelViewSet):
# #     queryset = Booking.objects.all()
# #     serializer_class = BookingSerializer
# #     permission_classes = [IsAuthenticatedOrReadOnly]
    
# #     def create(self, request, *args, **kwargs):
# #         # Attach the user
# #         serializer = self.get_serializer(data=request.data)
# #         serializer.is_valid(raise_exception=True)
# #         booking = serializer.save(user=request.user)

# #         # Initiate payment via Chapa
# #         amount = booking.total_price
# #         booking_reference = str(booking.booking_id)
# #         checkout_url, transaction_id = initiate_payment(
# #             amount=amount,
# #             booking_reference=booking_reference,
# #             user_email=user_email
# #         )

# #         # Save payment info
# #         Payments.objects.create(
# #             user=request.user,
# #             booking_reference=booking_reference,
# #             amount=amount,
# #             transaction_id=transaction_id,
# #             status="Pending"
# #         )

# #         # Return custom response
# #         return Response({
# #             "status": "success",
# #             "booking_id": booking.booking_id,
# #             "checkout_url": checkout_url
# #         }, status=status.HTTP_201_CREATED)


# import requests
# from rest_framework import viewsets, status
# from rest_framework.response import Response
# from rest_framework.permissions import IsAuthenticated
# from django.conf import settings
# from .models import Booking, Payments
# from .serializers import BookingSerializer


# class BookingViewSet(viewsets.ModelViewSet):
#     queryset = Booking.objects.all()
#     serializer_class = BookingSerializer
#     permission_classes = [IsAuthenticated]

#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         booking = serializer.save(user=request.user)

#         try:
#             checkout_url, transaction_id = initiate_payment(
#                 request=request,
#                 amount=booking.total_price,
#                 booking_reference=booking.booking_id,  # ✅ Use booking ID as tx_ref
#                 user_email=request.user.email
#             )

#             # Save transaction to Payments model
#             Payments.objects.create(
#                 user=request.user,
#                 booking_reference=booking.booking_id,
#                 amount=booking.total_price,
#                 transaction_id=transaction_id,
#                 status="Pending"
#             )

#             return Response({
#                 "status": "success",
#                 "booking_id": booking.booking_id,
#                 "checkout_url": checkout_url
#             }, status=201)

#         except Exception as e:
#             return Response({
#                 "status": "failed",
#                 "message": str(e)
#             }, status=400)


#     def initiate_payment(amount, booking_reference, user_email):
#         headers = {
#             "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
#             "Content-Type": "application/json"
#         }

#         payload = {
#             "amount": str(amount),  # ✅ Chapa expects string
#             "currency": "ETB",      # ✅ or your default currency
#             "email": user_email,
#             "tx_ref": str(booking_reference),  # ✅ Unique transaction reference
#             "callback_url": "http://127.0.0.1:8000/api/payments/verify/",
#             "return_url": "http://127.0.0.1:8000/payment/success/",
#             "customization": {
#                 "title": "ALX Travel App Booking",
#                 "description": "Payment for booking on ALX Travel App"
#             }
#         }

#         response = requests.post(CHAPA_URL, json=payload, headers=headers)
#         data = response.json()

#         if response.status_code == 200 and data.get("status") == "success":
#             return data["data"]["checkout_url"], data["data"]["tx_ref"]
#         else:
#             raise Exception(f"Payment initiation failed: {data.get('message', 'Unknown error')}")



# # from rest_framework.response import Response
# # from rest_framework.decorators import api_view
# # from rest_framework import status
# # from .models import Booking, Payments
# # from .services.chapa import initiate_chapa_payment

# # @api_view(["POST"])
# # def create_booking(request):
# #     try:
# #         user = request.user
# #         listing = request.data.get("property_id")
# #         start_date = request.data.get("start_date")
# #         end_date = request.data.get("end_date")
# #         total_price = request.data.get("total_price")

# #         # 1️⃣ Save booking
# #         booking = Booking.objects.create(
# #             user=user,
# #             property_id=listing,
# #             start_date=start_date,
# #             end_date=end_date,
# #             total_price=total_price,
# #             status="pending"
# #         )

# #         # 2️⃣ Create payment record
# #         payment = Payments.objects.create(
# #             user=user,
# #             booking_reference=str(booking.booking_id),
# #             amount=booking.total_price,
# #             status="Pending"
# #         )

# #         # 3️⃣ Get Chapa checkout link
# #         checkout_url, tx_ref = initiate_chapa_payment(payment)
# #         payment.transaction_id = tx_ref
# #         payment.chapa_checkout_url = checkout_url
# #         payment.save()

# #         return Response({
# #             "status": "success",
# #             "booking_id": booking.booking_id,
# #             "checkout_url": checkout_url
# #         }, status=status.HTTP_201_CREATED)

# #     except Exception as e:
# #         return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



# # from .services.chapa import verify_chapa_payment
# # from .tasks import send_booking_confirmation_email

# # @api_view(["GET"])
# # def verify_payment(request):
# #     tx_ref = request.query_params.get("tx_ref")

# #     try:
# #         payment = Payments.objects.get(transaction_id=tx_ref)
# #         result = verify_chapa_payment(tx_ref)

# #         if result.get("status") == "success" and result["data"]["status"] == "success":
# #             # ✅ Update payment
# #             payment.status = "Completed"
# #             payment.save()

# #             # ✅ Update booking
# #             booking = Booking.objects.get(booking_id=payment.booking_reference)
# #             booking.status = "confirmed"
# #             booking.save()

# #             # ✅ Send confirmation email
# #             send_booking_confirmation_email.delay(
# #                 payment.user.email,
# #                 booking.booking_id,
# #                 payment.user.first_name,
# #                 booking.property.title,
# #                 booking.start_date,
# #                 booking.end_date
# #             )

# #             return Response({
# #                 "status": "success",
# #                 "message": "Payment successful! Booking confirmed."
# #             })

# #         payment.status = "Failed"
# #         payment.save()
# #         return Response({"status": "failed", "message": "Payment failed!"}, status=400)

# #     except Payments.DoesNotExist:
# #         return Response({"error": "Payment not found"}, status=404)

# import requests
# from django.conf import settings
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from .models import Payments

# CHAPA_URL = "https://api.chapa.co/v1/transaction/initialize"
# CHAPA_VERIFY_URL = "https://api.chapa.co/v1/transaction/verify/"

# # -------------------
# # 1. Initiate Payment
# # -------------------
# @csrf_exempt
# def initiate_payment(request):
#     if request.method == "POST":
#         data = request.POST
#         amount = data.get("amount")
#         email = data.get("email")
#         booking_ref = data.get("booking_reference")

#         # Prepare Chapa API request
#         headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}
#         payload = {
#             "amount": amount,
#             "currency": "ETB",
#             "email": email,
#             "tx_ref": booking_ref,
#             "callback_url": "http://127.0.0.1:8000/api/verify-payment/",
#             "return_url": "http://127.0.0.1:8000/payment-success/",
#             "first_name": request.user.first_name if request.user.is_authenticated else "Guest",
#             "last_name": request.user.last_name if request.user.is_authenticated else "User",
#         }

#         response = requests.post(CHAPA_URL, headers=headers, json=payload)
#         chapa_response = response.json()

#         if chapa_response.get("status") == "success":
#             transaction_id = chapa_response["data"]["tx_ref"]

#             # Save payment in DB
#             Payments.objects.create(
#                 user=request.user if request.user.is_authenticated else None,
#                 booking_reference=booking_ref,
#                 amount=amount,
#                 transaction_id=transaction_id,
#                 status="Pending"
#             )

#             return JsonResponse({"payment_url": chapa_response["data"]["checkout_url"]}, status=200)
#         else:
#             return JsonResponse({"error": "Payment initiation failed"}, status=400)

#     return JsonResponse({"error": "Invalid request method"}, status=405)


# # -------------------
# # 2. Verify Payment
# # -------------------
# @csrf_exempt
# def verify_payment(request):
#     if request.method == "GET":
#         tx_ref = request.GET.get("tx_ref")
#         headers = {"Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}"}
#         response = requests.get(CHAPA_VERIFY_URL + tx_ref, headers=headers)
#         chapa_response = response.json()

#         try:
#             payment = Payments.objects.get(transaction_id=tx_ref)
#         except Payments.DoesNotExist:
#             return JsonResponse({"error": "Payment not found"}, status=404)

#         if chapa_response.get("status") == "success" and chapa_response["data"]["status"] == "success":
#             payment.status = "Completed"
#             payment.save()
#             return JsonResponse({"message": "Payment verified successfully"}, status=200)
#         else:
#             payment.status = "Failed"
#             payment.save()
#             return JsonResponse({"message": "Payment failed"}, status=400)

#     return JsonResponse({"error": "Invalid request method"}, status=405)
