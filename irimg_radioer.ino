// -*- mode: C++ -*-

// parameters
#define SEND_DELAY 20
#define LOOP_DELAY 100  // beyond blinking
#define MY_ADDRESS 2
#define HOST_ADDRESS 1


#include <SPI.h>
#include <RH_RF69.h>
#include <RHReliableDatagram.h>
#include <Wire.h>
#include <Adafruit_AMG88xx.h>

/************ Radio Setup ***************/

// Change to 434.0 or other frequency, must match RX's freq!
#define RF69_FREQ 433.0

#if defined (__AVR_ATmega32U4__) // Feather 32u4 w/Radio
  #define RFM69_CS      8
  #define RFM69_INT     7
  #define RFM69_RST     4
  #define LED           13
#endif

#if defined(ADAFRUIT_FEATHER_M0) // Feather M0 w/Radio
  #define RFM69_CS      8
  #define RFM69_INT     3
  #define RFM69_RST     4
  #define LED           13
#endif

#if defined (__AVR_ATmega328P__)  // Feather 328P w/wing
  #define RFM69_INT     3  // 
  #define RFM69_CS      4  //
  #define RFM69_RST     2  // "A"
  #define LED           13
#endif

#if defined(ESP8266)    // ESP8266 feather w/wing
  #define RFM69_CS      2    // "E"
  #define RFM69_IRQ     15   // "B"
  #define RFM69_RST     16   // "D"
  #define LED           0
#endif

#if defined(ESP32)    // ESP32 feather w/wing
  #define RFM69_RST     13   // same as LED
  #define RFM69_CS      33   // "B"
  #define RFM69_INT     27   // "A"
  #define LED           13
#endif

/* Teensy 3.x w/wing
#define RFM69_RST     9   // "A"
#define RFM69_CS      10   // "B"
#define RFM69_IRQ     4    // "C"
#define RFM69_IRQN    digitalPinToInterrupt(RFM69_IRQ )
*/
 
/* WICED Feather w/wing 
#define RFM69_RST     PA4     // "A"
#define RFM69_CS      PB4     // "B"
#define RFM69_IRQ     PA15    // "C"
#define RFM69_IRQN    RFM69_IRQ
*/

// Singleton instance of the radio driver
RH_RF69 rf69(RFM69_CS, RFM69_INT);
RHReliableDatagram rf69_manager(rf69, MY_ADDRESS);

// IR sensor
Adafruit_AMG88xx amg;
#define AMG_88xx_ROW_LEN 8

void setup() 
{
  Serial.begin(115200);
  while (!Serial) { delay(1); } // wait until serial console is open, remove if not tethered to computer

  pinMode(LED, OUTPUT);     
  pinMode(RFM69_RST, OUTPUT);
  digitalWrite(RFM69_RST, LOW);

  Serial.println("Feather RFM69 RX Test!");
  Serial.println();

  // manual reset
  digitalWrite(RFM69_RST, HIGH);
  delay(10);
  digitalWrite(RFM69_RST, LOW);
  delay(10);
  
  if (!rf69_manager.init()) {
    Serial.println("RFM69 radio init failed");
    while (1);
  }
  rf69_manager.setTimeout(100);
  rf69_manager.setRetries(8);
  Serial.println("RFM69 radio init OK!");
  
  // Defaults after init are 434.0MHz, modulation GFSK_Rb250Fd250, +13dbM (for low power module)
  // No encryption
  if (!rf69.setFrequency(RF69_FREQ)) {
    Serial.println("setFrequency failed");
  }

  // If you are using a high power RF69 eg RFM69HW, you *must* set a Tx power with the
  // ishighpowermodule flag set like this:
  rf69.setTxPower(20, true);  // range from 14-20 for power, 2nd arg must be true for 69HCW

  // The encryption key has to be the same as the one in the server
  // this is 'radioplusIRiscoo' -> integers
  uint8_t key[] = {114, 97, 100, 105, 111, 112, 108, 117, 115, 73, 82, 105, 115, 99, 111, 111};
  rf69.setEncryptionKey(key);
  
  pinMode(LED, OUTPUT);

  Serial.print("RFM69 radio @");  Serial.print((int)RF69_FREQ);  Serial.println(" MHz");

  bool status = amg.begin();
    if (!status) {
        Serial.println("Could not find a valid AMG88xx sensor, check wiring!");
        while (1);
    }

  delay(100); // let sensor boot up
  Serial.println("AMG88xx sensor init OK!");
  Serial.print("Starting up with key:");
  for (int i=0; i < 16; i++) { 
    Serial.print((char)key[i]);
  } Serial.println();
}


uint8_t recv_buf[RH_RF69_MAX_MESSAGE_LEN];

void loop() {
  uint8_t from, len = sizeof(recv_buf);
  
  if (rf69_manager.recvfromAckTimeout(recv_buf, &len, 2000, &from)) {
    recv_buf[len] = 0; // zero out remaining string
      
    Serial.print("Got message from #"); Serial.print(from);
    Serial.print(" RSSI :");
    Serial.print(rf69.lastRssi());
    Serial.println("");     
    if ((len > 0) && (from == HOST_ADDRESS)) {
      Serial.print("Got message from HOST: ");
      Serial.println((char*)recv_buf);
      if (recv_buf[0] == 't') {
        delay(150); // give receiver time to be prepared
        sendPixels();
      }
    }
    
  blink(LED, 30, 2); 
  delay(LOOP_DELAY);
   } else {
    Serial.println("timed out. Looping around");
   }
}

void sendPixels() {
  int i, j, row, pix4;
  float pixels[AMG88xx_PIXEL_ARRAY_SIZE];
  byte message[2*AMG_88xx_ROW_LEN+2];
  message[0] = 42;
  
  amg.readPixels(pixels);

  for (i=0; i<AMG88xx_PIXEL_ARRAY_SIZE; i++)  {
    row = i/AMG_88xx_ROW_LEN;
    j = i%AMG_88xx_ROW_LEN;
    if (j == 0) {
      message[1] = row; 
    }
    pix4 = (int) (pixels[i] * 4);
    message[2*j+2] = lowByte(pix4);
    message[2*j+3] = highByte(pix4);
    if (j+1 == AMG_88xx_ROW_LEN) {
      // send
      Serial.println("sending:");
      for (int k=0; k<(2*AMG_88xx_ROW_LEN+2); k++)  {
        Serial.print((int)message[k]);
        Serial.print(", ");
      } Serial.println("");
      
    
      if (!rf69_manager.sendtoWait((uint8_t *)message, 2*AMG_88xx_ROW_LEN+2, HOST_ADDRESS)) {
        Serial.print("Sending failed (no ack) on row number ");
        Serial.println(row);
        break;
      }  // otherwise keep going
    }
  }
}


int16_t packetnum = 0;
void ploop() {
  delay(1000);

  char radiopacket[20];

  (String("Hello World ") + String(packetnum++)).toCharArray(radiopacket, 20);
  
  Serial.print("Sending "); Serial.println(radiopacket);
  
  // Send a message to the DESTINATION!
  if (rf69_manager.sendtoWait((uint8_t *)radiopacket, strlen(radiopacket), HOST_ADDRESS)) {
    // Now wait for a reply from the server
    uint8_t len = sizeof(recv_buf);
    uint8_t from;   
    if (rf69_manager.recvfromAckTimeout(recv_buf, &len, 2000, &from)) {
      recv_buf[len] = 0; // zero out remaining string
      
      Serial.print("Got reply from #"); Serial.print(from);
      Serial.print(" [RSSI :");
      Serial.print(rf69.lastRssi());
      Serial.print("] : ");
      Serial.println((char*)recv_buf);     
      blink(LED, 40, 3); //blink LED 3 times, 40ms between blinks
    } else {
      Serial.println("No reply, is anyone listening?");
    }
  } else {
    Serial.println("Sending failed (no ack)");
  }
}

void nloop() {
  int i, j, row, pix4;
  float pixels[AMG88xx_PIXEL_ARRAY_SIZE];
  byte message[2*AMG_88xx_ROW_LEN+2];
  
  amg.readPixels(pixels);
  
  message[0] = 42;
  for (i=0; i<AMG88xx_PIXEL_ARRAY_SIZE; i++)  {
    row = i/AMG_88xx_ROW_LEN;
    j = i%AMG_88xx_ROW_LEN;
    if (j == 0) {
      message[1] = row; 
    }
    pix4 = (int) (pixels[i] * 4);
    message[2*j+2] = lowByte(pix4);
    message[2*j+3] = highByte(pix4);
    if (j+1 == AMG_88xx_ROW_LEN) {
      // send
      Serial.println("sending:");
      for (int k=0; k<(2*AMG_88xx_ROW_LEN+2); k++)  {
        Serial.print((int)message[k]);
        Serial.print(", ");
      } Serial.println("");

      rf69.send((uint8_t *)message, 2*AMG_88xx_ROW_LEN+2);
      rf69.waitPacketSent();
      delay(SEND_DELAY);
    }

    
  }
  
  blink(LED, 30, 2); 
  delay(LOOP_DELAY);
}



void blink(byte PIN, byte DELAY_MS, byte loops) {
  for (byte i=0; i<loops; i++)  {
    digitalWrite(PIN,HIGH);
    delay(DELAY_MS);
    digitalWrite(PIN,LOW);
    delay(DELAY_MS);
  }
}
