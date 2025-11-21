#ifndef ISR_CLOCK_H
#define ISR_CLOCK_H

// isrClock.h
// Minimal clock generator (Timer1, ISR-based) + D flip-flop helper
// Target: ATmega32u4 (e.g., Adafruit ItsyBitsy 32u4, Arduino Leonardo)
// Notes:
//  - When USE_INTERNAL_CLOCK == 1, a square wave is generated on PIN_CLK
//    using Timer1 Compare Match A ISR. The frequency is CLOCK_HZ.
//  - When USE_INTERNAL_CLOCK == 0, the library does not touch Timer1;
//    you may drive PIN_CLK externally and just use DFF_update().
//  - For simplicity and portability, the ISR toggles the pin via digitalWrite();
//    this is adequate for modest CLOCK_HZ. For higher rates, replace with
//    direct port writes.
//
// Usage in your .ino (example):
//   #include "isrClock.h"
//   #ifndef USE_INTERNAL_CLOCK
//   #define USE_INTERNAL_CLOCK 0
//   #endif
//   #ifndef CLOCK_HZ
//   #define CLOCK_HZ 10
//   #endif
//   #ifndef PIN_CLK
//   #define PIN_CLK 4
//   #endif
//   #ifndef CLOCK_LED_MIRROR
//   #define CLOCK_LED_MIRROR 0
//   #endif
//
//   void setup() {
//     // Initialize clock pin state for edge detection
//     __clk_prev = digitalRead(PIN_CLK);
//     // Start the hardware Timer1 clock on the chosen clock pin (if enabled)
//     #if USE_INTERNAL_CLOCK
//       T1Clock_begin(PIN_CLK, CLOCK_HZ);
//     #endif
//   }
//
//   void loop() {
//     // read clk with digitalRead(PIN_CLK) and do rising-edge detect as usual
//   }

#include <Arduino.h>
#include <avr/io.h>
#include <avr/interrupt.h>

#ifndef USE_INTERNAL_CLOCK
#define USE_INTERNAL_CLOCK 0
#endif

#ifndef CLOCK_HZ
#define CLOCK_HZ 10
#endif

#ifndef PIN_CLK
#define PIN_CLK 4
#endif

#ifndef CLOCK_LED_MIRROR
#define CLOCK_LED_MIRROR 0
#endif

// ----------------------
// D Flip-Flop helper
// ----------------------
// On a rising edge, capture D into Q (1-bit). Otherwise keep Q.
static inline uint8_t DFF_update(uint8_t Q, uint8_t D, bool risingEdge) {
  return risingEdge ? (D & 0x1) : (Q & 0x1);
}

// ----------------------
// Internal clock via Timer1 ISR (optional)
// ----------------------
#if USE_INTERNAL_CLOCK

// Current clock configuration
static volatile uint8_t  __isrclk_pin   = PIN_CLK;
static volatile uint8_t  __isrclk_state = LOW;

// Optionally mirror clock to LED (pin 13) for debugging
static inline void __isrclk_led_mirror(int level) {
#if CLOCK_LED_MIRROR
  digitalWrite(13, level);
#else
  (void)level;
#endif
}

// Choose a prescaler to fit OCR1A in 16-bit range for desired frequency.
// We generate a square wave by toggling the pin each ISR, so the ISR rate
// is 2 * CLOCK_HZ.
static bool __isrclk_choose_timer1(uint32_t hz, uint16_t* ocr1a_out, uint8_t* cs_bits_out) {
  if (hz == 0) hz = 1;
  const uint32_t toggle_rate = hz * 2UL;
  const uint32_t fcpu = F_CPU; // typically 16000000
  const struct { uint16_t div; uint8_t cs; } presc[] = {
    {1,   _BV(CS10)},
    {8,   _BV(CS11)},
    {64,  _BV(CS11) | _BV(CS10)},
    {256, _BV(CS12)},
    {1024,_BV(CS12) | _BV(CS10)},
  };
  for (uint8_t i = 0; i < sizeof(presc)/sizeof(presc[0]); ++i) {
    uint32_t ticks = fcpu / presc[i].div / toggle_rate;
    if (ticks >= 1 && ticks <= 65535) {
      *ocr1a_out = (uint16_t)(ticks - 1);
      *cs_bits_out = presc[i].cs;
      return true;
    }
  }
  // If we couldn't fit, clamp to max with largest prescaler
  *ocr1a_out = 65535;
  *cs_bits_out = _BV(CS12) | _BV(CS10); // 1024
  return false;
}

// Begin generating a square wave on 'pin' at 'hz' using Timer1.
static inline void T1Clock_begin(uint8_t pin, uint32_t hz) {
  __isrclk_pin = pin;
  __isrclk_state = LOW;
  pinMode(__isrclk_pin, OUTPUT);
  digitalWrite(__isrclk_pin, LOW);
#if CLOCK_LED_MIRROR
  pinMode(13, OUTPUT);
  digitalWrite(13, LOW);
#endif

  // Configure Timer1 in CTC mode, compare-A interrupt
  uint16_t ocr; uint8_t cs;
  __isrclk_choose_timer1(hz ? hz : CLOCK_HZ, &ocr, &cs);

  cli();
  TCCR1A = 0;
  TCCR1B = 0;
  // CTC mode: WGM12=1 (Mode 4)
  TCCR1B |= _BV(WGM12);
  // Set compare value
  OCR1A = ocr;
  // Clear pending, enable compare A interrupt
  TIFR1  |= _BV(OCF1A);
  TIMSK1 |= _BV(OCIE1A);
  // Set prescaler (starts the timer)
  TCCR1B |= cs;
  sei();
}

// Stop Timer1 clock generation and drive pin LOW
static inline void T1Clock_end() {
  cli();
  TIMSK1 &= ~_BV(OCIE1A);   // disable compare A interrupt
  TCCR1B &= ~(_BV(CS12) | _BV(CS11) | _BV(CS10)); // stop timer (no clock)
  sei();
  digitalWrite(__isrclk_pin, LOW);
#if CLOCK_LED_MIRROR
  digitalWrite(13, LOW);
#endif
  __isrclk_state = LOW;
}

// Timer1 compare A ISR: toggle the clock pin (and optional LED)
ISR(TIMER1_COMPA_vect) {
  __isrclk_state = (__isrclk_state == LOW) ? HIGH : LOW;
  digitalWrite(__isrclk_pin, __isrclk_state);
  __isrclk_led_mirror(__isrclk_state);
}

#endif // USE_INTERNAL_CLOCK

#endif // ISR_CLOCK_H
