import serial
import time

def read_raw_hardware_stream():
    print("=======================================================")
    print("OPENING RAW REGISTERS ANALYSIS PIPELINE VIA COM3")
    print("=======================================================")
    
    try:
        # Establish a raw, unfiltered serial link to your plugged-in device
        port = serial.Serial(port="COM3", baudrate=115200, timeout=3.0)
        time.sleep(0.1)
        
        # Flush the background noise buffers
        port.reset_input_buffer()
        port.reset_output_buffer()
        
        # Transmit the data request command explicitly
        print("Transmitting raw execution call: 'data 1\\r\\n'")
        port.write(b"data 1\r\n")
        
        # Wait a short moment for the internal register processing loop to populate
        time.sleep(0.3)
        
        # Read every single byte currently sitting in the OS buffer queue
        raw_bytes = port.read_all()
        
        print("\n--- CAPTURED RAW BYTES DATA STREAM ---")
        print(raw_bytes)
        
        print("\n--- DECODED STRING DISPLAY TRANSLATION ---")
        print(raw_bytes.decode('utf-8', errors='ignore'))
        
        port.close()
        print("=======================================================")
        
    except Exception as err:
        print(f"Failed to communicate with physical COM3 hardware: {err}")

if __name__ == "__main__":
    read_raw_hardware_stream()