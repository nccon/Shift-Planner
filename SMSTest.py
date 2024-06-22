import serial
import time

# Configure the serial connection
gsm_serial = serial.Serial("/dev/ttyAMA0", baudrate=115200, timeout=1)

def send_sms(phone_number, message):
    try:
        gsm_serial.write(b'AT\r')
        time.sleep(1)
        gsm_serial.write(b'AT+CMGF=1\r')  # Set SMS mode to text
        time.sleep(1)
        gsm_serial.write(f'AT+CMGS="{phone_number}"\r'.encode())
        time.sleep(1)
        gsm_serial.write(message.encode() + b"\x1A\r")
        time.sleep(1)
        print("SMS sent successfully!")
    except Exception as e:
        print(f"Failed to send SMS: {str(e)}")

# Example usage
if __name__ == "__main__":
    send_sms("your_phone_here", "Hello from GSM module!")
    gsm_serial.close()
