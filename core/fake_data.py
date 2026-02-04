import random
import string
import re

def generate_fake_data(context_text: str, data_type: str):
    """
    Generates context-aware fake data.
    """
    if data_type == "payment_proof":
        amounts = re.findall(r'\d{3,5}', context_text)
        amount = amounts[0] if amounts else random.choice(["500", "1000", "2000"])
        tid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        return (
            f"|| [FWD: SBI Alert] Rs.{amount}.00 debited from a/c XXXXX8932 "
            f"via UPI Ref {tid}. If not done by you, call 1800-SBI-FAIL. ||"
        )
    
    # --- NEW: THE WRONG OTP GENERATOR ---
    if data_type == "otp":
        # Generate a 6-digit code that looks real but is random
        fake_otp = random.randint(100000, 999999)
        return f"|| Is this the code? {fake_otp} ||"
    
    if data_type == "battery_low":
        return "|| [System] Battery Low (2%). Please charge device. ||"
        
    return ""