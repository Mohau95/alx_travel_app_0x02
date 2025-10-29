import os

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from models import Payment

CHAPA_SECRET_KEY = os.getenv("CHAPA_SECRET_KEY")
CHAPA_BASE_URL = "https://api.chapa.co/v1/transaction"


@csrf_exempt
def initiate_payment(request):
    """
    Initiates a payment with Chapa
    """
    if request.method == "POST":
        data = request.POST
        booking_reference = data.get("booking_reference")
        amount = data.get("amount")
        email = data.get("email")

        payload = {
            "amount": amount,
            "currency": "ETB",
            "email": email,
            "tx_ref": booking_reference,
            "callback_url": "http://localhost:8000/api/verify-payment/"
        }

        headers = {
            "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(f"{CHAPA_BASE_URL}/initialize", json=payload, headers=headers)
        res_data = response.json()

        if res_data.get("status") == "success":
            Payment.objects.create(
                booking_reference=booking_reference,
                transaction_id=res_data["data"]["id"],
                amount=amount,
                status="Pending"
            )
            return JsonResponse({"payment_url": res_data["data"]["checkout_url"]})
        else:
            return JsonResponse({"error": "Failed to initiate payment"}, status=400)
    return None


@csrf_exempt
def verify_payment(transaction_id):
    """
    Verify payment status from Chapa
    """
    headers = {
        "Authorization": f"Bearer {CHAPA_SECRET_KEY}",
    }

    response = requests.get(f"{CHAPA_BASE_URL}/{transaction_id}/verify", headers=headers)
    res_data = response.json()

    try:
        payment = Payment.objects.get(transaction_id=transaction_id)
    except Payment.DoesNotExist:
        return JsonResponse({"error": "Payment not found"}, status=404)

    if res_data.get("status") == "success" and res_data["data"]["status"] == "success":
        payment.status = "Completed"
        payment.save()
        # TODO: send confirmation email
        return JsonResponse({"status": "Payment completed"})
    else:
        payment.status = "Failed"
        payment.save()
        return JsonResponse({"status": "Payment failed"})
