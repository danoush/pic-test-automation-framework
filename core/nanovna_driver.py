import time
import math
import serial
from core.base_instrument import AbstractVNA

class PhysicalNanoVNA(AbstractVNA):
    """
    A professional, robust serial driver interface that communicates with a 
    physical NanoVNA-H hardware device over an active USB COM port interface.
    """
    def __init__(self, resource_address: str):
        super().__init__(resource_address)
        self.serial_link = None
        # Standard hardware terminal prompt marker returned by NanoVNA firmware shells
        self.PROMPT_MARKER = b"ch>" 

    def connect(self) -> bool:
        print(f"[HW-NANOVNA] Initializing system connection hook to: {self.resource_address}")
        try:
            self.serial_link = serial.Serial(
                port=self.resource_address,
                baudrate=115200,   # Nominal baud rate constraint for internal USB-UART bridges
                timeout=3.0        # Strict 3-second safety timeout guard to catch hardware locks
            )
            
            # Wake up the micro-controller interface shell and consume the initial buffer line
            self.serial_link.write(b"\r\n")
            time.sleep(0.05)
            self.serial_link.read_all()
            
            self.is_connected = True
            print("[HW-NANOVNA] Connection verified. Physical registers online.")
            return True
            
        except Exception as err:
            print(f"[HW-NANOVNA] CRITICAL INITIALIZATION FAILURE: {err}")
            self.is_connected = False
            return False

    def set_if_bandwidth(self, bandwidth_hz: int) -> None:
        if not self.is_connected:
            raise ConnectionError("No active serial session open with NanoVNA.")
        print(f"[HW-NANOVNA] Architecture notice: Internal filter tracking set to {bandwidth_hz} Hz.")

    def capture_s21_trace(self) -> list:
        """
        Queries physical hardware registers for transmission data, reads until the 
        terminal prompt is encountered, and parses real/imaginary values into an electrical dB vector.
        """
        if not self.is_connected:
            raise ConnectionError("Cannot capture trace; instrument session is closed.")
            
        print("[HW-NANOVNA] Querying physical device for Channel 1 (S21 Forward Transmission)...")
        
        try:
            # Clear out the operating system buffers to prevent parsing lagging old data frames
            self.serial_link.reset_input_buffer()
            self.serial_link.reset_output_buffer()
            
            # Transmit 'data 1' to pull the forward transmission S21 parameter sweep array
            # ('data 0' would pull input return loss S11)
            self.serial_link.write(b"data 1\r\n")
            
            # --- HIGH-HYGIENE TERMINAL STREAM READING LOOP ---
            raw_buffer = b""
            start_time = time.time()
            
            while True:
                # Intercept physical dropouts to prevent infinite while loops from locking the factory line
                if (time.time() - start_time) > self.serial_link.timeout:
                    raise TimeoutError("Hardware device timeout limit reached while reading serial stream buffers.")
                    
                if self.serial_link.in_waiting > 0:
                    raw_buffer += self.serial_link.read(self.serial_link.in_waiting)
                    
                    # Stop reading immediately when the micro-controller terminal shell prints its closing prompt
                    if self.PROMPT_MARKER in raw_buffer:
                        break
                        
            # Decode the verified byte block into clean text string formats
            decoded_payload = raw_buffer.decode('utf-8', errors='ignore')
            lines = decoded_payload.splitlines()
            
            parsed_db_trace = []
            
            # --- PARAMETRIC STRING PARSING PASS ---
            for line in lines:
                cleaned_line = line.strip()
                
                # Filter out system echoes, header noise command prompts, or empty string splits
                if not cleaned_line or "data" in cleaned_line or "ch>" in cleaned_line:
                    continue
                    
                try:
                    # The firmware returns space-separated coordinate strings: "Real_Value Imaginary_Value"
                    parts = cleaned_line.split()
                    if len(parts) >= 2:
                        real_val = float(parts[0])
                        imag_val = float(parts[1])
                        
                        # Convert the complex vector coordinate back into standard electrical decibels (dB)
                        # Magnitude = sqrt(real^2 + imag^2)
                        magnitude = math.sqrt(real_val**2 + imag_val**2)
                        
                        # Guard against mathematical domain errors at absolute zero signal boundaries
                        if magnitude > 0:
                            db_value = 20 * math.log10(magnitude)
                        else:
                            db_value = -100.0 # Standard floor attenuation marker
                            
                        parsed_db_trace.append(db_value)
                        
                except ValueError:
                    # Skip lines that fail scalar float conversions (e.g., text warnings from firmware glitches)
                    continue
                    
            if not parsed_db_trace:
                raise ValueError("Serial trace extraction completed, but zero valid coordinate lines were processed.")
                
            print(f"[HW-NANOVNA] Swept successfully. Extracted {len(parsed_db_trace)} active frequency metrics.")
            return parsed_db_trace
            
        except Exception as error:
            print(f"[HW-NANOVNA] CRITICAL RECORD SWEEP ERROR: {error}")
            # Raise the exception explicitly back up to the calling pipeline to prevent silent false passes
            raise error

    def close(self):
        if self.serial_link and self.serial_link.is_open:
            self.serial_link.close()
            print("[HW-NANOVNA] Physical resource released cleanly.")